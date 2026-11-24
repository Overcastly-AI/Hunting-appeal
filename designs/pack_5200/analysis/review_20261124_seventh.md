# Review 7: iteration 1 (BL-061 frame, BL-062/064 weight, BL-063 looks) — design-reviewer, 2026-11-24

Saved by the orchestrator from the reviewer's report (the reviewer is read-only).

**Counts: 2 blockers, 8 majors, 10 minors.** Verdict: CF-LITE's "passes every HA-LS-1 row" is not shown yet; concept C is not lighter on the rubric's base metric and its plinth can't be made for build 1. Mass arithmetic otherwise checks.

Ran: tests/test_frame_iter1.py, test_looks_iter1.py, test_iter1_weight.py, test_materials.py all pass; `mfg_corrie_f_rev3.py --check` min SF 1.36 (B-25), 32 load points; rebuilt CF-LITE and checked connectivity; recomputed Volkersen, tube scaling and mass rows. Confirmed: tubes 200.0 g, MMA 24.06 g, Ti bolts 9.9 g, z 234 hardware 27.98 g, CF-LITE −34.5 g; option A −82.3 g/+$8.37 (as booked), B −139.2, C −232.1; H1 baseline reproduces bl058.json.

## Blockers
- **B1 FE body is not three parts.** `frame_iter1.py:361-362` cuts part gaps only inside the stay column (r < 17, `:74`). Rebuilt CF-LITE printed body is one connected component (86,436 voxels); at z 193, 132 voxels (528 mm², ~264 mm²/side, > 236 mm² sleeve) cross P1/P2 at r 17–27; 5 at z 469. Load bypasses the bonds. Also no exported print geometry (RUBRIC:7). Fix: real part-boundary cuts, re-run check('cflite'), re-derive bonds, test P1/P2/P3 are separate components.
- **B2 Governing bond margin unconservative.** (a) Volkersen uses E·t for torque transfer (`:614-615`); G·t gives k 12.48→19.61 at P3 (×1.57). (b) `tube_resultants` (`:566-583`) reads N/M/T ~6 % low (0.939). (c) `BOND_PA_MPA = 5.0` (`:78`) is the top of the range, from a PU adhesive on MJF PA12; cited epoxies 3.7 MPa; no MMA-on-PAHT-CF value. Combined P3 ≈ 0.66 (≈0.49 at 3.7). Fix: split axial/torque, real ring stiffness, design 3.7×0.8 = 2.96 MPa until T6p-T, sleeve submodel with real tube GJ.

## Majors
- **M1** C8 (hipbelt-off ultimate, "no damage", proof-loaded in T1(c)) judged on average bond stress (`load_standard.md:115`) relies on MMA yielding; cited PA data fail adhesively. P3 peak 0.57, P1 0.91. Fix: peak ≥ 1.0 at C8 where printed side governs, or a substrate clause in HA-LS-1; size T6p-T on C8.
- **M2** Fail-safe M4 bolt checked only for tube-wall bearing (`:652-657`). Printed-sleeve bearing (37.6 MPa) margin ~0.3 at P3, ~0.5 at P1; no open-hole knock-down on the tube. Fix: add both checks; extend T6b.
- **M3** T6p-T pass line references transfers not stored in the json; covers P3 only; not in the register. Fix: dN/dT per sleeve in json, numeric pass lines, P1-band and P2 coupons, register it.
- **M4** Buckling 1.31 uses the member proxy shown to overstate H1. Fix: `voxel_buckling.linear_buckling` on H1 and CF-LITE.
- **M5** Concept C deltas on ledger basis: base proven now +3.0 g, base after tests +15.2 g, as-hunted after tests +7.0 g (lid is as-hunted only; B-06 already 70D after tests). `concepts_mass.py:63-66`, `design_language.md:190,203`, DECISIONS.
- **M6** Plinth: B-02u is structural 630D with no small-batch print source; printing means HyperD on a zip-carrying piece (brief rule 4.6). Fallback not producible either.
- **M7** C triples printed camo area (0.201→0.628 m²/set) on the skyline; provenance unsigned and image-level originality compare (incl. KUIU Verde 2.0) never run (`camo/originality_check.md:20-29`). Gate C on both.
- **M8** Mesh savings from booked 380 g/m², re-sourced 350: N1 ≈ −36 g, N2 ≈ −3.2 g, option A ≈ −64 g (not −82.3).

## Minors
m1 KUIU 2 lb 15.9 oz = 1358 g (suspension inference 1044 g; 826 g if lid included, flipping "ours lighter"). m2 stale numbers (RUBRIC 3.99 kg, rollup 3986.8, frame_iter1 research 1453 g, design_language buckling 1.05, iter1_weight queued fixes unapplied). m3 "+55 g" H1-box claim unsourced. m4 "318 g outside print" ≈ 336 g. m5 test gaps (cflite tube mass, torque path, part separation). m6 brief contradicts C (120 mm min vs 75 mm kick strip; one zone per view; black locks stand out on tan cap). m7 render shows whole roll camo; no empty/day/bag-off views. m8 tube strength max-stress isotropic, not Tsai-Wu layup (1.20, no change yet). m9 RT/RTM unrated; give RT a rating. m10 CF-LITE does not lift the H1 R1 hold.

## Looks per RUBRIC (C as adopted): 1 FAIL (roll ends, side clutter), 2 FAIL (W1/W2 slant), 3 PASS, 4 FAIL (lid locks, guy lines, grey mesh), 5 FAIL (frame). Reviewer 1/5 vs author 3.5/5.
