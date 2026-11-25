# Ninth independent review (BL-084): B81-Lb and D83-L aluminium frames

Reviewer: design-reviewer, 2026-11-25. Scope: `designs/pack_5200/iter2/frame_b/bl081.md|json`,
`designs/pack_5200/iter2/frame_d/bl083.md|json`, `cut/*.dxf`, `huntkit/gendesign/bl081_*.py`, `bl083_*.py`,
`huntkit/fea/tube_solid.py`, `data/materials/metals/alu_6061_t6*.yaml`, against HA-LS-1 rev C
(`load_standard.md`) and `docs/RUBRIC.md`. No design file was edited.

What I ran:
- `python -m pytest -q tests/test_bl081_concept_b.py tests/test_bl083_concept_d.py`: **14 passed** (5.2 s). The tests
  check wiring and that the record is self-consistent. They do not check any of the findings below.
- I reran `bl081_concept_b.evaluate_global` and the BL-081 clamp submodel (`bl081_local.clamp_combined_hoop`,
  `tube_solid`). I reproduce the governing row exactly: hoop 93.5 -> 122.2 MPa, fatigue 1.019, static 1.123.
  Then I ran the sensitivities quoted below: preload sweep, mid tee, as-drawn stay-top end condition, C6p,
  strut end fixity.
- I parsed both DXFs with ezdxf (hole-to-edge and hole-to-bend distances) and measured the printed-socket STLs
  with trimesh.

## Verdicts

| option | verdict | why, in one line |
|---|---|---|
| **B81-Lb** | **NOT READY for a build pack** | The governing upper tee is analysed on geometry that does not exist: the 50 mm shell overhangs the 530 mm stay top and collides with the stay-top collar, and the as-drawn end condition gives 0.65 static and 0.67 fatigue (B1). The hose-band tee has no geometry and its upper band does not fit (B2). The preload window is narrower than worm-drive scatter (B3). The cost-cap pass rests on an unpriced LOCAL-METAL assumption (M6). |
| **D83-L** | **NOT READY** | It shares B1-B3, because the stays, tees and bands are B81's. It also fails the cost gate by USD 82 even at the raised USD 160 cap. The pan itself is close: fix M3 and M4, re-run, and get a real SendCutSend quote. |
| (B81 / D83 bolted, for reference) | not ready | B1, B3 (bolted window -16 % / +6 %) and M1 (mid tee at 1.00, unreported) apply to them too. |

Both options become "ready after fixes" only after B1-B4 are closed by a re-analysis on the as-built tee
geometry plus a clamp fatigue coupon. Neither option can go to a build pack on the current record.

## Blockers

**B1. The governing upper-tee clamp is analysed on a continuous tube, but it actually sits on the stay's free end, and the
drawn parts collide.** All four variants are affected.
- Where: `huntkit/gendesign/bl081_concept_b.py:171` (`clamp_len` 50, tee at z 520). Stay length 530 mm
  (`bl081_parts.py:275`, nodes SL520 / SL530). `bl081_local.py:462-482` (`clamp_units`: L 130 mm, clamp centred
  with 40 mm of tube above it and a clamped end 13 mm below the IM3 loop). `bl081_parts.py:136`
  (`stay_top_collar` sleeves the stay OD at z 515-533, OD 31.4 mm).
- Failure: the shells run from z 495 to 545, so they overhang the tube end (z 530) by 15 mm. Over z 515-530 they
  occupy the same space as the stay-top collar (shell bore 25.4 mm vs collar OD 31.4 mm), so the parts as drawn
  cannot be assembled. Only about 35 mm of the shell bears on tube, and that length ends at a free tube end with no
  ring stiffening above it. I reran the authors' own solid submodel (same `TubeFE`, same jaw / loop / edge unit loads
  and magnitudes, same Goodman formula) with a 200 mm stay ending at the clamp's z 530 point and the clamp pressure
  on the 35 mm of tube. The same preload (2 x 2000 N) gives hoop 151.6 -> 240.7 MPa: **fatigue 0.67, static 0.65**
  (record: 1.02 / 1.12). As a control, moving the fixed end away without the free end changes the record only
  1.019 -> 1.014, so the drop comes from the end condition.
- Fix: move the upper tee down so the shells stay fully on tube, clear of the collar (for example centre at about
  z 490 with the IM3 loop below it), or lengthen the stays by 30 mm or more. Then re-run `clamp_units` with the real end
  condition: clamp_units needs a "free end at x" option, and the leg and bushing sit inside this zone. Update OV-1 to the
  new position. Re-run every row that uses tee link stiffness or tee position.

**B2. The B81-Lb / D83-L hose-band tee has no design and does not fit the existing parts.**
- Where: `bl083_report.py:110` (B81-Lb = B81 cfg + `tees: bands`), `bl083_concept_d.py:555-577` (`band_cfg` only
  rescales the preload), `bl083_parts.py:424-458` (bill only). There are no STL, cut-list, jig or socket changes for
  bands.
- Failure: the bolted B81 routes the bar end through a PAHT socket that is held by the bar bolt only
  (`bl081_parts.py:117-129`), and the backers and bolts are what hold the clamp stack together. Removing the backers
  leaves nothing defined to retain the socket. Measured from the STLs, the upper socket occupies z 503.3-536.7 on a
  shell running z 495-545. That leaves 8.3 mm either side for a 9 mm W4 band, and the band housing is wider than that.
  The upper band would also sit above the stay top (z 530), where it can only squeeze the PAHT collar or the crown
  bushing. That breaks the BL-082 rule of no printed part under preload. The clamp FE still uses the jaw-patch field
  of the bolted backers (`clamp_units`), not a band field: the pressure is under two 9 mm bands and there is a band gap
  at the worm housing.
- Fix: design the band tee as real geometry. Lengthen the shells, or put the socket between the bands and give it a
  positive mechanical lock to the shells. Model the band pressure field in `tube_solid`. Emit STL, cut list and jigs.
  Then re-run.

**B3. The governing detail only works inside a preload window narrower than real tightening scatter.**
- Where: `bl081_local.py:559-572` (fatigue mean = installed preload), `:506-519` (slip with retention),
  `bl083_concept_d.py:142` (`band_T_upper` 1000 N, 3.3 N m), `:148-152` (K 0.55, d 6 mm, no cited torque-tension
  test). The info row in `bl083.json` says it outright: "full 4.0 N m (2424 N) drops the wall fatigue row below 1".
- Failure: from my sweep of the record's own functions at the upper tee:

  | installed preload per side (N) | 1700 | 1800 | 1900 | 2000 | 2100 | 2200 | 2400 |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | wall fatigue margin | 1.07 | 1.05 | 1.03 | 1.02 | 1.005 | **0.99** | **0.96** |
  | slip, bolted (ret. 0.9) | 1.01 | 1.07 | 1.13 | 1.19 | 1.25 | 1.31 | 1.43 |
  | slip, bands (ret. 0.8) | **0.90** | **0.95** | 1.004 | 1.06 | 1.11 | 1.16 | 1.27 |

  The bands are feasible only from about 1890 N to about 2130 N (-5 % / +6.5 %). Bolted B81 / D83 run from about
  1680 N to 2130 N. Torque-controlled M5 A2 scatters about +/-25 %. A worm-drive band set by feel to 3.3 N m, with
  an assumed K, will not hold +/-5 %. No torque screwdriver is in the tool list either.
- Fix: make the joint insensitive to preload. Move the clamp off the free end (B1), lengthen or thicken the shells so
  the hoop mean drops, or carry the bar shear in bearing (a pin, which BL-082 forbids at the stay top, or a
  shoulder) so slip is not a strength row. Specify preload control: a torque screwdriver at a measured K from CL-B,
  or a band with a defined-tension spring. Show both margins at the plus and minus scatter limits.

**B4. The governing fatigue row (1.02) uses a mean curve with no scatter or fretting allowance, and no coupon covers
this detail.**
- Where: `data/materials/metals/alu_6061_t6.yaml:23-26,72-77` (Yahr best fit; "These are MEAN curves, not allowables";
  Yahr design curve = fit / 2 on stress). `bl081_local.py:564-568`. Coupons in `bl081.md:165-172` and
  `bl083.md:252-258`.
- Failure: at 1.02 on the mean curve, the expected chance of a crack by 1e5 walking cycles is about 50 %. On the
  Yahr design curve the same row is 0.70. The detail is a clamp edge on a bending tube. That is a classic fretting-
  fatigue site, and the knock-down for aluminium is commonly 0.5-0.7 on strength. Only "Kt 2" is applied to the beam
  stress, with no source. FRET-50 is a gross-slip criterion, and I checked it at walking load (utilisation 0.15).
  It does not exclude edge micro-slip from stay bending inside the shell. The BL-082 rule ("fatigue < 1.2 needs a
  coupon") is met by KF-1 / KF-D, but those test a crush-sleeved bolt hole, not this clamp. CL-1 / CL-B are
  static, and SC-1 cycles 150 N of cinch only.
- Fix: add a clamp fatigue coupon ("KF-T"). Use the real tee, at the real stay-end position, at the specified
  preload including the plus-scatter limit. Cycle stay bending plus the IM3 loop at 1.2 x walk to 1e5 (or 2e5) cycles,
  n 3, and dye-check under the shell edges. Until KF-T passes, require a margin of at least 1.2 on the mean curve, or
  at least 1.0 with a stated scatter factor, for this row.

## Major

**M1. The mid tee (z 330) wall is not checked, and it sits at 1.00 in bolted form.** `bl081_local.py:555-572` checks
only the upper tee. The mid tee carries a higher preload (2600 N bolted, 2424 N bands), the IM2 loop (403 N
factored, `bl081_local.py:694`), and the worst stay beam stress in the frame, because the stay member margin is governed
at SL330-SL374. On the record's own functions (edge couple from `tee_*330|M` = 25.7 N m): bolted
**fatigue 1.000**, static 1.16; bands at nominal 1.03; bands at +20 % preload 0.95. Fix: add the mid-tee rows to
`clamp_rows` and treat them like B3.

**M2. C6p (tall load on extension posts) is skipped without a note.** `bl081_concept_b.py:508`,
`bl083_concept_d.py:419`, `bl080_metal_frame.py:397`: `if case.name == "tall_load_posts": continue`. HA-LS-1
(`load_standard.md:104`) and DECISIONS 2026-11-07 keep C6p. I ran it on B81. It does not govern the tees, but it
lowers the stay member margin from 1.767 to 1.743 at 23 in (SL330-374). Through `sb` that takes the upper-tee
fatigue row to about 1.01 and the mid tee below 1.0. The crown leg reaches 1.39. Fix: include C6p in the envelope, or
document N/A with the owner's agreement. Do not drop it silently.

**M3. The D83 pan wall bolt at z 85 has a 7.0 mm edge (e/D 1.32), but the check and the coupon assume 12 mm (e/D
2.3).** DXF `cut/hip_pan_tray_5052_flat.dxf`: holes D5.3 at (+/-144.8, 29.9) sit 7.0 mm from the wall's bottom edge
(wall z 78, bolt z 85). `bl083_concept_d.py:461-462` takes e/D from `wall_aft` (12 mm) only. BB-D uses a "12 mm edge"
strip (`bl083_report.py:170`). The stay pushes down on this bolt, toward that edge. e/D 1.32 is below the usual
1.5 minimum. The pin-loaded fatigue check (`:476-481`) uses a 24 mm ligament, but the real ligament to that edge is
4.35 mm. Fix: lower the wall bottom edge to z 70 or less (e/D of at least 2 in every load direction), regenerate the
DXF, and make BB-D match the part.

**M4. The 5052-H32 basis has no material record, and its fatigue allowable exceeds yield.** No 5052 YAML exists in
`data/materials/` (CLAUDE.md: every number traces to a record). The values are hard-coded at
`bl083_concept_d.py:63-72`, with the fatigue limit from a "search snippet, secondary". `sn_5052_smax_r0`
(`:75-82`) scales the whole 6061 Yahr curve by 117 / 96.5, which gives Sa(1e5) = 172.5 MPa: 0.81 x the *minimum* UTS,
because it mixes a typical endurance with a minimum UTS. The R 0 Smax of 191 MPa is above the minimum yield of
159 MPa, and nothing caps it. Capping at yield moves the pan wall fatigue 1.62 -> 1.35 and the face + spine 1.74
-> 1.45. They still pass, but the basis is wrong. Fix: the materials-engineer adds
`data/materials/metals/alu_5052_h32.yaml` with cited B209 minimums and an S-N source for 5052. Cap Smax at Fy.

**M5. The anodise factor is not wired into the governing row, and no finish is specified.**
`bl081_concept_b.py:134` (`ANODISED_HOLES = False`) only affects `fat_allow_local`. The clamp row computes Sf directly
(`bl081_local.py:566-567`), so turning the switch on would not change the governing row. No cut list, part note or
build note says "do not anodise the stays or clamp zones" (grep finds the requirement only inside the ASSUMPTION
text). Applied to Sf, ANODISE-FAT 0.7 takes the upper tee to 0.85 (0.71 if applied to the whole Goodman line). Owners
often anodise frames for looks, which the rubric's third axis encourages. Fix: route the clamp and pan fatigue rows
through one allowable function that honours the switch. Put "stays bare or Type II <= 10 um, clamp zones and holes
masked" on the cut list. Also note the galvanic pair: A2 bolts and bands on bare 6061, wet.

**M6. The B81-Lb cap pass rests on unpriced assumptions, and the cap was moved to admit it.** Per
`bl083_parts.py:454` and `bl083.md:178`, the -USD 18.00 comes from "ASSUMPTION LOCAL-METAL: same list price, no
shipping". Bands are USD 1.50 each "not read" (`bl083_concept_d.py:152`), and SHELL-PRICE (USD 15) was never read.
RUBRIC §1b says "every price from a material record or a cited shop page". With the cited shipping basis, B81-Lb
costs **USD 174.76**, over both the USD 150 and the USD 160 cap. `RUBRIC.md:14` raised the cap specifically to admit
B81-Lb at USD 156.76. Fix: get a real local quote, or book shipping. Read the band and shell listings. Report the
cap decision against the shipped figure.

**M7. The B81-Lb margins table reports doubler credit that B81-Lb does not have.** `bl083_report.py:93-99`
(`_b81l_stations`) swaps the doubled-wall tube (t 2.49 mm) into every stay gusset-bolt station for *both* lever runs.
`check_b81l(stay="t1000_065")` (`:228`) reuses it, but its bill has no doubler (`thin_stays=False`). Result:
`bl083.md:215` shows "stay z135 gusset bolt R (doubled wall): fatigue 1.48", where the real value on the .065 wall is
1.05 (B81, `bl081.md:23`). It does not change the minimum, but the published table is wrong. Fix: apply
`_b81l_stations` only when `stay == "t1000_049"`.

**M8. The PAHT bar socket is the only bar-to-clamp load path, and only its compression is checked.**
`bl081_parts.py:117-129` describes the socket as a saddle that reaches 3 mm past the shell's inner tangent, with the
M5 bar bolt bearing in PAHT and no fastener to the shells. The global model treats the tee as a full 6-DOF link
(2e4 N/mm, 2e8 N mm/rad, `bl081_concept_b.py:231-232`) and carries up to 1.22 kN and 50 N m (`tee_*520`, C8 / C3)
through it. The only socket row is "pawl 1334 x 1.5 / 2 in compression" (`bl081_local.py:597-599`). There are no
checks for bar-bolt bearing in PAHT, socket bending under the couple, torque about the stay, or retention if the bar
goes into tension. Fix: give the socket a mechanical lock to the shells or backers (metal path), or model the link
with the stiffness and capacity the socket actually has. Add the bearing and creep rows.

**M9. The D83 proof test HP-D does not exercise the governing pan case.** The pan wall strength margin is 1.10 in
`side_hill_torsion` (`bl083.json`, row "pan side walls"), but HP-D loads only pin V + H (`bl083_report.py:174-177`).
The grillage (strips plus truss diagonals) is coarse for a 1.10 margin on a plate with bends and holes. Fix: add a
torsion step to HP-D (+/- stay-top couple at the C3 level), or check the wall with a plate FE.

**M10. The CL-B coupon is specified at a torque the design forbids.** `bl083_report.py:182-186` sets the CL-B band
torque to 4.0 N m. The design sets the upper bands to 3.3 N m, because at 4.0 N m the wall fatigue fails (B3). The
coupon would qualify slip at a preload the frame cannot use. `bl083.md` §8 still lists the bolted CL-1 for D83-L.
Fix: test at the design torque and at the plus and minus scatter limits. Measure band tension by strain to get K.
Publish the D83-L coupon list in the md.

## Minor

- m1 `bl081_local.py:469-477`: the clamp submodel's clamped end is 13 mm below the IM3 loop patch, which stiffens
  ovalisation. It is a small effect (1.019 vs 1.014 with the end moved 83 mm away), but put the boundary at least
  3 R away by default.
- m2 `bl083.md:24,137,268` and the `cost_table` `within_cap` (`bl083_parts.py:398`) still use cap 150. RUBRIC now
  says 160. Make it one constant.
- m3 Spreader `skin_pressure` FAILS on B81 (14.06 kPa vs 14, `bl081.md:86`). It is not carried into the margin table
  or the verdict. Report it as a failing comfort row or justify the limit.
- m4 Crush sleeves (`bl081_concept_b.py:67`): a flat-ended 7.9 mm sleeve in a 22.1 mm bore leaves a 0.73 mm saddle gap at
  its sides. `crush_rows` assumes a full 25 mm2 annulus. Specify the sleeve length to the chord at the sleeve OD with a
  tolerance (+0/-0.1), and a printed length gauge for a beginner with a hacksaw.
- m5 Tooling: the proving list's tubing cutter goes to 1-1/8 in, but the shell stock is 1-1/4 in. No torque
  screwdriver (1-5 N m) is listed, and B3 needs one. Both fit under the USD 50 tool rule. Add them.
- m6 SendCutSend die: hole-to-bend 7.1 mm passes only against the smallest die (0.472 in, half-width 6.0 mm). For
  .100 in, SCS may use the 0.630 in die (8.0 mm), which would fail. Confirm in the SCS bend calculator before
  ordering, or move the four flange holes to 8.5 mm or more.
- m7 D83 relies on one M5 rod and nut for buckling (0.99 without the strut, 1.52 with it). I confirmed that a pin-ended
  strut gives 1.61, so end fixity is not the issue, but a loose nut is. Specify a nylon-insert locknut or
  threadlocker, a preload, and a T-check "rod tight" step.
- m8 No creep row for the PAHT parts under sustained load (saddle plugs, sockets, foot cups). The margins are large
  (7.9-44), but the rubric scores creep. Add the rows on the `creep_rupture_8h_40c_ratio` basis.
- m9 `bl081_concept_b.py:20-25` docstring still describes printed clamps, IM2 / IM3 on backers and the bar end bolted
  to the backers. That contradicts `bl081_parts.py:117-120`. Fix the docstring, because B2 and M8 hinge on it.
- m10 The tube_props ring limits (`bl081_concept_b.py:160`) are the 1 x .049 values applied to 1 x .065. That is
  conservative, but label it.

## Checks that hold up

- HA-LS-1 envelope: C1-C5, C6, C7 and C8 at 15 / 19 / 23 in, both couple tops, factors from `load_standard.py`.
  Float attachment cases covered by IM3 1415 N > 1142 N. Buckling rule = eigen / (1.5 x case factor). Only C6p is
  missing (M2).
- Goodman arithmetic, Kf = Kt (q 1) and the R 0 Smax of 190.9 MPa match the 6061 record. The 6061 S-basis 241 / 290 are
  correctly sourced.
- D83 lumbar strut: buckling 0.99 -> 1.52 reproduced. It is not sensitive to end fixity (1.61 pin-ended).
- Mass and cost arithmetic: the deltas B81 -> B81-Lb (1815.6 g, USD 156.76) and D83 -> D83-L (1674.3 g, USD 242.54)
  recompute exactly. Stock buys fit the cut lengths. The DXF flats close, have CUT / BEND / NOTE layers, units mm, and
  hole counts match the cut list.
- Manufacturability (beginner, hand tools + Bambu H2S): the metal is all straight cuts and jig-drilled holes. PAHT-CF
  is within the H2S envelope, and the pan is outsourced. The real risks are the shell sawing and fit (CLAMP-UNIFORM
  depends on extruded 1-1/4 x .125 ID tolerance vs drawn 1 in OD), sleeve lengths (m4) and band torque (B3). Add an
  ID / OD check to OV-1.

## What to re-run after the fixes

1. Fix the tee geometry (B1, B2, M8) and the `clamp_units` end condition. Then re-run `bl081_report` and
   `bl083_report stage B81-Lb / D83-L`.
2. Add the mid-tee rows (M1) and C6p (M2). Report every clamp row at nominal and at the plus and minus preload
   scatter limits (B3).
3. Add the 5052 record (M4), the anodise routing and finish callout (M5), and fix the B81-Lb station leak (M7).
4. Coupons KF-T (B4) and CL-B at the design torque (M10) before any build pack.
