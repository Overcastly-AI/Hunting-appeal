# Review 8 (2026-11-25): PPA-CF frame work (BL-069 records, BL-070 H1-P)

Reviewer: independent adversarial review (design-reviewer). I did not write any of the work reviewed here. I edited
only this file and committed nothing.

Scope: `data/materials/polymers/ppa_cf_fdm.yaml`, `pps_cf_fdm_bambu.yaml`, `docs/backlog/BL-069-ppu-frame-material.md`,
`docs/backlog/BL-070-h1-ppa.md`, `huntkit/gendesign/bl070_h1p.py`, `tests/test_bl070_h1p.py`,
`designs/pack_5200/iter1/frame/bl070_h1p.{json,md}`, and the STLs in `designs/pack_5200/iter1/frame/h1p/`. Baselines:
`analysis/bl065.md`, `analysis/bl058.json`. Rules: HA-LS-1 rev C (`analysis/load_standard.md`).

**Counts: 2 blockers, 8 majors, 8 minors.**

## What I re-ran and what holds up

- `python -m pytest -q tests/test_bl070_h1p.py`: 13 passed (88 s). `tests/test_materials_bl069.py`: 5 passed.
- **The whole-body rows were really computed on the exported STL.** I re-rastered `h1p/h1_assembled.stl` and re-ran
  `check_body` from scratch on fine_sm8.cyc and beam, with output sent to my scratch directory. R1 came out 1.0757,
  strength 1.699, creep 3.155, and the z 234 joint 1.646 / **1.051** on beam. These match the record to the digit.
  `test_checked_raster_is_the_exported_stl` also passes (re-raster equals `g1_solid.npz`).
- **Mass bookkeeping is right.** STL volume 1 014 488 mm3 x 1.25 g/cm3 = **1268.1 g**. That is lower half 610.8 +
  upper half 620.3 + two clevises at 18.5 g each. The PAHT baseline is 1 008 794 mm3 x 1.06 = 1069.3 g, matching
  `bl058.json:3171`. The STL is watertight with one shell. The hardware delta of +2.4 g comes from 1.1 g per nut,
  0.7 g of extra Ti per screw, and 1.5 g per insert (`insert_heatset_brass_m5.yaml:26`). That traces.
- **The H1-P clevis STLs are the released clevises.** Volumes match to 0.01 mm3, so a clevis row taken from the H1
  interface run is legitimate.
- The rows that take the TDS straight (density, E, XY/Z tensile, Charpy, Tg, process windows) trace to the cited
  Bambu TDS.

The findings follow. Severity: **blocker** means a margin or gate as written does not protect the design. **Major**
means a margin is optimistic or a gate is weak, but it can be fixed inside this ticket. **Minor** means wording,
tests or bookkeeping.

---

## BLOCKERS

### B-1. Hip through-bolt rows (7.54 / 4.24 / 12.45) rest on a washer that cannot fit; on the real nut face the fatigue row fails 1.15
- `huntkit/gendesign/bl070_h1p.py:425-427, 465-466`, `bl070_h1p.py:1011-1013` (NUT-BEAR),
  `designs/pack_5200/iter1/frame/bl070_h1p.md:19-21`, `docs/backlog/BL-070-h1-ppa.md:42, 103-109`,
  `tests/test_bl070_h1p.py:100-101`.
- **Failure.** Bearing is booked on a D10 / D5.5 ring (54.8 mm2 -> 1800 N). The trap cut at `bl070_h1p.py:600` is an
  **8.12 AF hex** (inscribed D8.12), so a D10 washer cannot sit in it. The seat only sees the nut's bearing face:
  - DIN 934 / ISO 4032 M5, dw min 6.9 mm: 13.6 mm2 -> 448 N.
  - Even the full hex face is only 31.7 mm2 -> 1040 N.

  On the code's own rule (`T` values in `bl070_h1p.json` h1p.hip_mount.rows):

  | bearing area | strength (C2, T 238.6 N), goal 1.5 | fatigue (walk, T 127.3 N), goal 1.15 | creep (carry, T 79.5 N), goal 1.5 |
  |---|---:|---:|---:|
  | D10 ring, 54.8 mm2 (as booked) | 7.54 | 4.24 | 12.45 |
  | full hex face, 31.7 mm2 | 4.36 | 2.45 | 7.20 |
  | **dw 6.9 ring, 13.6 mm2 (ISO 4032)** | **1.88** | **1.06 FAIL** | 3.10 |

  The H1-P hip mount is no better than the inserts it replaced (1.056). The "through-bolts lift the hip row" claim
  falls.
- **Also not addressed:**
  - **No preload or torque is specified anywhere in BL-070.** The creep row uses only the external carry tension
    (79.5 N). A preloaded joint keeps preload on the nut seat permanently. A "normal" M5 snug of 1 N m (K 0.2) is
    about 1000 N, which puts 74 MPa on the dw ring against a knocked Z of 32.9 MPa. The seat crushes, PPA creeps, and
    the preload relaxes, so the mount rocks on the boss face.
  - **Thread engagement is zero-protrusion.** M5 x 20 minus a 3 mm flange minus the 13 mm seat leaves exactly the
    4 mm nut height (`frame_h1.JOINT.nut_t` 4.0), so the screw tip is flush with the top of the nut. The DIN 7984
    tip chamfer leaves about 3.2 mm of real thread, and Loctite 243 will not reach full strength.
  - The 3 mm flange is itself ASSUMPTION FLANGE-RIGID. The drawn mount is D44 x 1.2 with no holes
    (`h1_closeout.py:273, 641`).
  - The downstream BL-071 draft (`designs/pack_5200/frame_h1p_build.py:85, 345-349, 921-925`, untracked, not under
    review) already found the dw issue and the 1.06. **The BL-070 record that every consumer reads was not
    corrected.**
- **Fix.**
  - Re-book NUT-BEAR on dw 6.9 mm (or design a round washer pocket: D10.5 x 1.2 deep counterbore at the seat, then the
    hex above it, and book the D10 ring).
  - Re-run `hip_inserts` and the record, and change the test at `tests/test_bl070_h1p.py:100-101` to assert the dw
    ring.
  - Specify a torque in BL-070, and make the creep row `max(preload, T_carry)`.
  - Use M5 x 22 (or 25) so the screw shows at least 1.5 threads through the nut.
  - Until fatigue is >= 1.15, the hip row is a FAIL. Remedies include a D10 washer pocket, a 12-bolt pattern, or
    flanged nuts (DIN 6923 M5, dc 11.8, which needs a round pocket).

### B-2. The "hot/wet" knock-down is wet-only at 23 C, and the gate coupon (CA-3) tests at 23 C, so it cannot catch the hot loss
- `data/materials/polymers/ppa_cf_fdm.yaml:38-43, 57, 78`, `huntkit/gendesign/bl070_h1p.py:688-699`,
  `docs/backlog/BL-070-h1-ppa.md:163`, `BL-069...md:89, 186-187`.
- **Failure.** HA-LS-1 section 4 keeps a **hot/wet** knock-down on the allowables. PAHT's 0.8 is booked as hot/wet,
  and BL-069's table labels PPA's 0.73 "x hot/wet knock". Even the insert rule calls it "hot 0.73"
  (`bl070_h1p.py:449`). But 0.73 = Raise3D 122 / Bambu 168:
  - a **23 C** room-temperature test;
  - after **annealing** 100 C 8 h (which raises strength);
  - after only **3 days ambient** (nowhere near saturation for a 4 mm bar);
  - on a different grade (density 1.15 against 1.25).

  The only temperature data in the record (Fiberlogy PPA-CF15, `ppa_cf_fdm.yaml:71`) shows UTS 0.86 at 40 C dry. A
  polyamide's Tg also falls with absorbed water. The note "40 and 60 C are below Tg 85 C" (`:78`) uses the dry DSC Tg.

  Hot and wet together at 0.73 x 0.86 = 0.63 scale the interlayer-governed rows by 0.86:
  - **R1 1.076 -> 0.93;**
  - **z 234 joint fatigue 1.051 -> 0.90;**
  - static fatigue 1.87 -> 1.61.

  CA-3-PPA tests conditioned coupons at 23 C only, after 14 d at 23 C / 50 % RH. A 4 mm PA bar does not reach
  equilibrium in 14 d at 23 C. So CA-3 can pass while the hot/wet margin is below 1.
- **Fix.**
  - Split the factor in the record into `wet_knockdown_ratio` (data) and `hot_40c_ratio` (ASSUMPTION, about 0.86 from
    Fiberlogy) and apply both.
  - Run CA-3-PPA (Z tensile and SBS) **at 40 C** on coupons conditioned **to constant mass** (ISO 1110: 70 C /
    62 % RH, weighed to <= 0.1 % change). Record the uptake against the 1.30 % TDS value.
  - Re-derive the pass lines from the hot/wet margin.
  - If R1 drops below 1, H1-P needs another growth step before any build.

---

## MAJORS

### M-1. R1 (1.076) and z 234 joint fatigue (1.051) each fall below 1.0 under ONE reasonably worse, in-record assumption
- `ppa_cf_fdm.yaml:37, 62, 78`, `bl070_h1p.md:11, 14`, `BL-070...md:49-50`.
- Both rows are 83-98 % interlayer-shear governed. LINEAR-Z holds (I checked the term shares in the cache), so each
  row scales directly:

  | worse assumption (one at a time) | source of the worse value | R1 | z 234 joint fatigue |
  |---|---|---:|---:|
  | fatigue ratio 0.25 instead of 0.30 | low end of the range the record cites (Sofia PA12-CF15, 0.25-0.32; frame_comp_A 2.2) | **0.90** | **0.88** |
  | design Z = 57 - 3.41 x 5 = 39.9 (B-basis for an ISO 527 n = 5 set) instead of 57 - 2.4 SD | the TDS gives +/- 5 with no n; **"2.4 SD" has no source anywhere** (frame_comp_A.md:52 just states it) | **0.95** | **0.93** |
  | knocked Z = Raise3D conditioned Z 30.2 (the only measured conditioned Z) | `ppa_cf_fdm.yaml:42`; the note at `:78` says it "sits at the design Z" but it is **8 % below** 32.85 | **0.99** | **0.97** |
  | interlayer shear 0.55 x Z instead of 0.6 (unsourced ratio) | INTERLAYER-0.6 has no PPA source | **0.99** | **0.96** |

- The record presents H1-P as "passes every HA-LS-1 row on PPA design values". Those design values are less
  conservative than the record's own data.
- **Fix.**
  - State the 2.4 factor's basis or replace it with a tolerance factor tied to the TDS n. Correct the "sits at" wording
    in the YAML note.
  - Report the four sensitivities next to the margins in `bl070_h1p.md`.
  - Either target R1 / joint >= 1.15 in the design loop (the BL-021 scatter goal used for the lug and hip), or say
    plainly that H1-P is a coupon-gated design whose margins are inside assumption scatter.

### M-2. The new nut traps sit in the R1 hot spot and raise local fatigue utilisation 61 %; FI99 and the analytic hip rows both miss it
- `bl070_h1p.py:597-601` (trap cut), `bl070_h1p.py:465-477` (hip rows are pure hand calcs, no geometry).
- **Measured on the H1-P STL** (my manifold section at y -34):
  - The 8 hex traps at 9.19-9.2 mm pitch **merge in pairs**: four pockets of 116.6 mm2 = 2 x 57 mm2.
  - The remaining webs between the pairs are **0.99 mm**.
  - At y -30 the traps break out of the boss's side wall.
- **Fatigue utilisation** (cached `util_*_fine_sm8.cyc.npz`), within 9 mm of the bolt axes at y -40..-26:

  | | max | voxels > 1.0 |
  |---|---:|---:|
  | H1 (no traps) | 2.24 | 48 |
  | **H1-P** | **3.61** | **128** |

  - The peak is at (+-17, -33, 103), next to the hex corner of the bottom traps, on the shear_xy term.
  - 550 of the 999 top-1 % voxels are within 35 mm of the boss axis.
  - The FI99 rule discards the top 1 %, so this does not show in R1.
- **Fix.**
  - Run a local submodel of the boss (0.5 mm mesh, traps exact) on the fine_sm8.cyc sets.
  - Rotate the hexes so flats face the neighbour, or drop to 6 bolts / a wider ring so the webs are >= 3 mm (3
    extrusion widths at 0.6).
  - Round the pocket floors and corners with r >= 1 mm.
  - Re-check R1 and the hip rows with the traps as cut.

### M-3. CA-1-PPA does not test the governing failure mode and gives almost no reliability
- `bl070_h1p.py:676, 680-687`, `BL-070...md:162`.
- **Wrong mode.** The governing fatigue term is interlayer shear (shear_xy 83 % / shear_yz 9 % of the R1 top 1 %).
  CA-1 runs R 0.1 tension coupons, so it does not measure interlayer shear fatigue, and no cited source covers it.
- **Weak statistics.** "All 6 run out at 1e5" with no life or load factor demonstrates only R61/C95 (0.05^(1/6)). It
  is also run at 23 C only.
- **Pass ratio set from R1 alone.** The pass ratio is 0.30 / R1 = 0.279. The z 234 joint fatigue (1.051) and the
  clevis fatigue (1.21 / goal 1.15) need 0.285. A batch with a true ratio of 0.28 passes CA-1 and leaves the joint at
  0.98. This is covered only if the conditioned mean is >= 33.6 MPa, which the line does not state.
- **Fix.**
  - Add short-beam-shear fatigue (R 0.1, D2344 geometry, Smax = 0.30 x 0.6 x 32.85 / 1.051 = 5.6 MPa as an absolute
    stress).
  - Set the ratio from min(R1, joint, clevis / 1.15 x 1.0).
  - Run to 4e5 cycles (scatter factor 4) or at 1.15 x Smax.
  - Run at 40 C after conditioning to constant mass (B-2).

### M-4. Coupon statistics and representativeness: mean - 2.4 SD at n = 6 is short of B-basis, and lone coupons over-read interlayer bond
- `bl070_h1p.py:692-695`, `BL-070...md:163`.
- **The factor is short.** The one-sided 90/95 tolerance factor is 3.01 at n = 6 (2.36 at n = 10, 3.41 at n = 5). I
  simulated 200 000 normal batches of 6. A population whose true 10th percentile sits exactly on the line passes
  "mean - 2.4 SD" **11 %** of the time: about 89 % confidence, not 95 %.
- **The coupons do not match the frame's print history.**
  - Interlayer strength depends strongly on layer time. A lone ISO 527 1A Z bar printed standing (170 mm tall, about
    10 x 4 mm section) lays each layer in seconds. A frame half takes minutes per layer at 65 C chamber.
  - The coupon over-reads the frame's interlayer bond, which is the governing allowable.
  - Standing 1A bars also wobble at height.
- **Fix.**
  - Use k = 3.01 for n = 6, or n = 10 at 2.36.
  - Cut Z and SBS coupons from a printed block (or wall) whose layer time matches a frame half: print it beside a
    half, or add a time-matched dummy.
  - Report each batch's layer time.

### M-5. Plate contact: both halves stand on supports, and the mouse-ear and brim plan cannot be built as written
- `BL-070...md:137-145, 152`, `bl070_h1p.md:78-81`, `BL-069...md:167`.
- **Measured on the flat STLs:**
  - The upper half's 163 mm2 is a **single patch at one end** of the 309 mm part: x 273-302, y 118-163. Within 1 mm
    of the plate there are 1445 mm2, all at that same end.
  - The lower half touches only at the D50 hip-boss face: x 129-179, 1773 mm2.
  - The stay feet and "upper stay ends" are **not on the plate**, so the specified 20 mm mouse-ear discs
    (`BL-070...md:143`) cannot be added.
  - The 15 mm brim only rings those patches.
- **Risk.** About 600 g of PPA-CF per half, with 3x PAHT's modulus and crystallising at 178 C, hangs on same-material
  tree supports anchored at one end (upper half). That is the warp/curl scenario WARP names, and nothing in the plan
  acts on it. The "Both halves fit 340 x 320 with the brim" statement (`:152`) is moot rather than wrong.
- **Fix.**
  - Add printed sacrificial rafts or pads under the far end of the upper half and under both stay feet (tie them to
    the part with a 0.3 mm break line), or a flat plate-side datum strip in the export.
  - Book their filament.
  - Print a first-article upper half before the coupons are spent.

### M-6. The mid-print spool swap puts a pause layer at an uncontrolled height in an interlayer-governed frame
- `BL-070...md:147-149`, `bl070_h1p.md:80-81` (799 / 802 g against a 750 g spool), ASSUMPTION SPOOL-SWAP.
- **Failure.** A run-out pause leaves the top layer cooling while the owner swaps (minutes, or hours if overnight).
  That makes a weak interlayer plane at a random z. In this frame interlayer shear governs R1 and the joint, so the
  pause layer could land at the hip boss or lumbar struts.
- **Fix.**
  - Have the slicer place a planned filament change at a height (print z) outside the hot-spot band. Compute the
    band from `util_g1_*`.
  - Or verify AMS 2 Pro / HT auto-refill feeding PPA-CF on the H2S. Bambu's own compatibility statement needs
    citing.
  - Or splice the spools before printing.
  - Add a pause-layer SBS coupon to CA-3.

### M-7. Cold impact is under-covered: the coupon covers one stay at 24 J; the set-down at 33 J and the crown are never tested cold
- `bl070_h1p.py:708-718`, `BL-070...md:165`, `ppa_cf_fdm.yaml:64` (impact_minus20c_ratio 0.5, used by no
  calculation).
- **The material gap.** PPA's Z Charpy is 4.3 kJ/m2 against PAHT's 13.3 (x 0.32), and its Z elongation 0.9 % against
  5.2 %.
- **What T4c-PPA covers.** 3 coupons of the lower R stay with a 2.0 kg slug (2.0 x 9.81 x 1.22 = 23.9 J).
- **What it misses.**
  - HA-LS-1 T4b (68 kg dropped 50 mm onto one foot = **33 J**, five times per foot) is a larger hit on the same stay
    foot, and nobody runs it cold.
  - HA-LS-1 T4c (`load_standard.md:240`) has no temperature, so the full-frame tests will run warm.
  - Side-on and crown-top drops hit the upper half (crown corners, pawl housing, the 0.99 mm trap webs). No coupon
    covers them.
  - 3/3 pass on a brittle material is weak evidence.
- **Fix.**
  - Add a -20 C soak (>= 4 h) to the PPA frame's own T4b and T4c on P1, at the end of the sequence before T2u.
  - Add a crown-corner / upper-bar coupon.
  - Raise the stay coupons to 5.
  - Size the stay coupon drop to the T4b energy (33 J).

### M-8. The booked modulus ratio contradicts the record's own conditioned data, so the CA-4 gate is set on a non-governing number
- `ppa_cf_fdm.yaml:41, 58`, `bl070_h1p.py:86-90, 703-705`.
- **Contradiction.** The record holds E_xy conditioned 7800 against dry 11800, a ratio of **0.66 at 23 C**. The same
  cross-brand rule gives the strength knock-down 0.73. Yet `modulus_40c_wet_ratio` is 0.85 at **40 C and wet**.
- **Effect.**
  - E_buckle at 0.66 x 0.89 hot x 0.85 creep is about 5.9 GPa. Buckling 3.72 becomes about 2.6, which still passes.
  - The z 234 contact stiffness also uses E x E_hot (`frame_h1.py`, kc), so the bolt share shifts.
  - CA-4's pass line of ">= 0.85" will probably fail against data already in hand. That stops the build on a value
    whose governing need is 0.23 (buckling).
- **Fix.**
  - Book 0.66 x hot (ASSUMPTION) or state why 0.85.
  - Set the CA-4 line at what the governing rows need: buckling, and the joint-stiffness sensitivity, re-run at the
    lower E.

---

## MINORS

- **m-1. "Every row on the exported STL" overstates what was done.**
  - Clevis and hip rows come from `interfaces_h1.json` (H1). The clevis is identical, so that is fine. The hip rows
    are hand calculations with no geometry (see M-2).
  - Fix: say so in `BL-070...md:49-50`.
- **m-2. The re-raster is not a pure STL raster.**
  - The checked raster is the BL-058 `body_stl` rule: 115 493 STL voxels became 115 749, with 360 pads added
    (`finalize.json` reraster). That is the same rule as the baseline, so it is consistent, but undisclosed.
  - Fix: one line in `bl070_h1p.md`.
- **m-3. Tests.**
  - `tests/test_bl070_h1p.py:155-164` skips on a clean checkout (the cache is scratch), so the key RUBRIC-1 check
    never runs in CI.
  - `:132-139` only re-reads the record's own numbers.
  - `:100-101` locks in the D10 ring (B-1).
  - Fix: track the g1 raster as a released `npz` (or its hash) and assert against it. Assert the dw ring.
- **m-4. The CA-3 "if below" band is miscomputed.**
  - `bl070_h1p.py:698-699`, `BL-070...md:170-171`: "between 31.3 and 28 MPa R1 reads 0.9-1.0".
  - Actually R1 = 1.076 x Z / 32.85, which is 0.92-1.025, and the joint fatigue falls to 0.90 at 28 MPa.
  - Fix: state both rows.
- **m-5. Dryer.**
  - 120 C for 10 h on the supplied spool: the spool's temperature rating is not cited, and BED-DRY on the H2S bed is
    unverified.
  - Fix: cite Bambu's spool rating for PPA-CF or re-spool onto a metal spool. Specify a hygrometer below 20 % RH in
    the feed box for the whole 20 h.
- **m-6. Spool count.**
  - 3 spools (2250 g) against 799 + 802 g of halves leaves about 650 g for every coupon in CA-1, CA-3, CA-4 and
    T4c-PPA. No coupon filament estimate is given.
  - Fix: estimate the coupon grams, and book 4 spools if they exceed 600 g.
- **m-7. E-ISO.**
  - Isotropic G = E_xy / 2.7 over-credits interlayer shear stiffness in torsional and lateral modes. The layer-normal
    bound (x 0.364) gives 1.35, which still passes, but stacked with M-8 it reads about 0.95.
  - Fix: run one eigen at a transversely isotropic or G-reduced voxel E.
- **m-8. CA-4 strength line and pass statistic.**
  - "Flexural at 60 C dry >= 0.73 x 208" applies a wet ratio to a dry hot test. CA-4 also does not say whether its
    lines are on the mean or on every coupon.
  - Fix: use the hot ratio, and state mean - k SD.

---

## Summary table

| id | severity | row or claim affected | as booked | realistic | file:line |
|---|---|---|---|---|---|
| B-1 | blocker | hip mount fatigue (goal 1.15) | 4.24 | **1.06** (dw ring) | bl070_h1p.py:425, 465 |
| B-2 | blocker | R1 / joint fatigue, hot + wet | 1.076 / 1.051 | **0.93 / 0.90** | ppa_cf_fdm.yaml:57; bl070_h1p.py:688 |
| M-1 | major | R1 / joint under one worse assumption | 1.076 / 1.051 | 0.90-0.99 / 0.88-0.97 | ppa_cf_fdm.yaml:37, 62 |
| M-2 | major | local utilisation at the hip traps | not checked | 3.61 max (H1 2.24); 0.99 mm webs | bl070_h1p.py:597-601 |
| M-3 | major | CA-1 gate | tension, 6/6 | wrong mode, R61/C95 | bl070_h1p.py:676-687 |
| M-4 | major | CA-3 statistics / representativeness | k 2.4 | k 3.01 needed (n 6) | bl070_h1p.py:692 |
| M-5 | major | plate contact / warp plan | 163 mm2 + ears | one end only; ears impossible | BL-070...md:137-145 |
| M-6 | major | spool swap | staged spool | pause layer in an interlayer-governed body | BL-070...md:147 |
| M-7 | major | cold impact | 3 stay coupons, 24 J | T4b 33 J and crown untested cold | bl070_h1p.py:708 |
| M-8 | major | E ratio / CA-4 | 0.85 | 0.66 from the record's own data | ppa_cf_fdm.yaml:41, 58 |

**Verdict.** The FE on the export is real and reproducible, and the mass is right. But H1-P is not "passing every
HA-LS-1 row on design values":
- The hip row fails on the real nut face.
- R1 and the joint sit inside the scatter of their own assumptions.
- The CA-3 gate (and CA-1 for fatigue) cannot detect the hot/wet case that HA-LS-1 requires.

Do not release H1-P for printing until B-1 and B-2 are closed and CA-3 / CA-1 are re-specified per M-3 and M-4.
