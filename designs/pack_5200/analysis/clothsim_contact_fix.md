# BL-025 Cloth-sim contact-field fix and re-runs

Owner: pack-designer, 2026-11-12. Ticket: `docs/backlog/BL-025-clothsim-contact-fix.md`.
Code: `huntkit/clothsim/pack.py` (fix), `huntkit/clothsim/recontact.py` (re-evaluation of stored runs),
`designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py` (run folders per revision), `huntkit/gendesign/loadpath_check.py` (reader).
Numbers: `analysis/clothsim_contact_fix_results.json` (every stored run, every case: stored, reproduced and corrected
contact forces, and the spreader pass-through check), `concepts/corrie_f_sim/corrie_f_sim_results.json` (CORRIE F rows).
Run folders: `outputs/clothsim/corrie_f/` (not tracked; regenerate with the commands in section 6).

## 1. Summary

- **Bug fixed.** When the contact-rounding continuation stops early, `run_case` now restores the contact gap fields of
  the kept stage together with x, so every `contact_*` force and the spreader footprint/pressure in `results.json`
  come from the kept stage. Three regression tests (`tests/test_clothsim_contact_restore.py`) drive `run_case`
  on analytic plane fields and check the field and the force against hand values (120 N kept vs 100 N on the failed field).
- **Stored runs re-evaluated** (`recontact.py`, 125 run folders, 371 cases): on all 237 stopped cases from before the
  fix the old report is reproduced to 0.0 N on the field of the failed stage (so the diagnosis is right), and on the
  kept field their spreader force falls by 4 % to 99 % (frame and crown up or down). The 12 stopped cases run after
  the fix (this ticket's five sims) already report the kept field: the end-to-end check of the fix on the real sim. **No released or decision number changes:** no analysis
  used these forces as an input, except BL-021, which already re-evaluated them on the kept field (section 3).
- **Rev 0 / rev 1 split.** CORRIE F load runs now live in `F_r0_PR*` (BL-011, guys at x +/-100) and `F_r1_PR*`
  (BL-022, guys at x +/-52). The three rev 0 coarse runs were re-run and reproduce BL-011 exactly (IM3 552.4 / 515.5 /
  460.1 N at 15 / 19 / 23 in); `test_loadpath_check.py::test_a1_cf_per_torso_cheek` passes reading `F_r0_PR15`.
- **Guys-off IM3 disagreement explained.** The coarse 970 N guys-off run (`F_r1_PR15_goff_sm8` meat) is not a valid
  equilibrium: 56 bag nodes have tunnelled through the spreader face, up to 69.7 mm deep. No sound run has any.
- **Mesh / start scatter (task 4, fine h 25):** 23 in meat from 8 mm rounding vs 6 mm: IM3 561.8 vs 522.2 N
  (+7.6 %), CG y 132.4 vs 135.7 mm, CG z 488.2 vs 486.8 mm. Guys-off 15 in meat from 6 mm vs 8 mm: IM3 449.6 vs
  436.0 N (+3.1 %), CG y 201.3 vs 201.7 mm. The two fine guys-off runs agree; the coarse 970 N is an artefact.

Imperial: 1 N = 0.2248 lbf. 970 N = 218 lbf; 450 N = 101 lbf; 562 N = 126 lbf; 552.4 N = 124 lbf; 1116 N = 251 lbf.
CG 201.5 mm = 7.93 in; 132.4 / 135.7 mm = 5.21 / 5.34 in.

## 2. The fix (task 1)

`huntkit/clothsim/pack.py::run_case`: the gap fields of each converged stage are snapshotted with x
(`_contact_fields`); when a stage fails, x **and** the fields go back to the kept stage (`_restore_contact_fields`).
`report.summarize` evaluates the `contact_*` terms on the sim's current fields, so it now reports the kept stage.
Only contact forces and the spreader footprint block (touching %, contact area, mean pressure, gaps) were wrong:
strap, hook, hinge, seam forces, volume, CG and profile depend on x only and were always right.

Tests: `tests/test_clothsim_contact_restore.py` (stop mid-continuation, stop at the first stage, full continuation),
`tests/test_clothsim_recontact.py` (stage parsing, pass-through detector, the BL-021 case reproduced and corrected,
roll-up), `tests/test_corrie_f_run_dirs.py` (run-folder names, loadpath reads rev 0).

## 3. Who used the reported contact forces (task 2)

`python -m huntkit.clothsim.recontact <run dirs> --json ...` re-evaluates each stored case on (a) the field the old
report used (the last stage tried, from the solve log) and (b) the kept stage's field. `recontact.summarize` rolls it up.

| family | runs | cases | stopped (pre-fix / post-fix) | old report reproduced (max abs diff, pre-fix) | case-terms changed > 2 % | spreader change, range |
|---|---|---|---|---|---|---|
| attach_diet (BL-004) | 28 | 84 | 78 / 0 | 0.0 N | 227 | -4.0 to -65.9 % |
| shell_sweep (BL-009) | 25 | 74 | 71 / 0 | 0.0 N | 208 | -6.2 to -68.1 % |
| corrie_f (BL-011, BL-021, BL-022, BL-025) | 18 | 45 | 29 / 12 | 0.0 N | 87 | -5.7 to -99.1 % |
| top-level runs (CORRIE A–D, bag comp, v31 attachment / anchor studies) | 54 | 168 | 59 / 0 | 0.0 N | 173 | -4.6 to -92.9 % |

Not evaluated: the four `chert_*` runs (an older `results.json` without `scenario_file`). Cases whose first solve did
not converge (no continuation ran) never moved their fields and are unchanged.

Typical corrected values (stored -> kept): CORRIE F rev 1 15 in meat coarse spreader 1268 -> 1067 N (-16 %), fine
1332 -> 1116 N (-16 %; 1087 N in y, the BL-021 finding); fill cases -20 to -65 %; packed cases -50 to -80 % (small
forces). The spreader force always falls on the kept (rounder) field: the solver balanced the bag against that field,
and the sharper field reads extra penetration at the plate edges that is not in equilibrium.

Consumers, checked by search of every `results.json` reader (`contact_spreader`, `contact_frame`, `contact_crown`,
`spreader_footprint`, `mean_pressure_kpa`):

| analysis | what it read | affected? | change |
|---|---|---|---|
| BL-021 `im3_body_simloads` (H1 body, IM3 eye on sim loads) | contact node forces | **no**: it rebuilt the fields at `contact_rounding_mm` (the kept stage) itself | 0 % |
| BL-004 `attach_diet`, `attach_system_results.json` | `crown_contact_n` | recorded only; no check, limit or doc line uses it | n/a (values in the JSON) |
| `bag_top_anchor.py` (outputs table) | `crown_contact_n` | scratch table only | n/a |
| BL-009 shell sweep, BL-011 / BL-022 `corrie_f_sim` | IM3, hinges, CG, volume, R-28 profile | **no**: x-only quantities | 0 % |
| spreader / back-rail skin pressure (`spreader.py`, `back_rail.py`, BL-018) | own rev C load model | **no**: does not read the sim | 0 % |
| `report.py` PDF / PNG headline "Spreader contact N" | `contact_spreader` | scratch outputs only; correct on new runs | as table above |

Spreader pass-through (`recontact.pass_through`, every stored case): 5 cases. `F_r1_PR15_goff_sm8` meat (56 nodes,
70 mm: section 5); BL-004's `A_hinge_CORRIE_PR15` / `A_hinge_S15_PR15` meat (61–65 nodes, ~210 mm; those runs did not
converge and the variant was already rejected on that ground); `F_r1_PR23_sm8` fill (3 nodes, 30.6 mm) and
`S14_PR23` fill (1 node, 32.3 mm), both just over the 25 mm threshold at the spreader rim.

No design number in a tracked analysis changes by more than 2 %. The stored `results.json` files keep the old
contact numbers (they are scratch); `clothsim_contact_fix_results.json` holds the corrected value next to each.

## 4. Run folders per revision (task 3)

`corrie_f_sim.run_dir`: variant `F` (current rev, `corrie_f.REVISION` = 1) -> `F_r1_PR{t}{tag}`; variant `Fr0` -> `F_r0_PR{t}{tag}`.
The packed render drape keeps `F_PR{t}_fine` (read by `huntkit/viz3d/corrie_f.py`). In the scratch tree the old names
are symlinks to the r1 folders (and `F_PR15_fine_meat_BL021` to its r0 folder), so BL-021's reader still finds its runs.
`loadpath_check.corrie_f_loads` reads `F_r0_PR{t}` (A1-CF is a rev 0 check) and reports the folder it read.

Rev 0 coarse re-runs (`corrie_f_sim.py run Fr0 --torso t`), IM3 max(R, L) at 1 g:

| torso | BL-011 frozen | re-run | kept rounding fill / meat |
|---|---|---|---|
| 15 in | 552.4 N (meat), 439.6 N (fill) | 552.4 / 439.6 N | 6 / 6 mm |
| 19 in | 515.5 / 363.6 N | 515.5 / 363.6 N | 6 / 6 mm |
| 23 in | 460.1 / 336.3 N | 460.1 / 336.3 N | 4 / 2 mm |

The test failed before because `F_PR15` held the rev 1 run (547.7 N); it now passes on the rev 0 run, for the right reason.

## 5. Mesh scatter: second fine 23 in meat and fine guys-off 15 in (task 4)

Fine mesh (h 25), CORRIE F rev 1 (guys at x +/-52 unless off), meat case at 1 g, add-ons on. CG with externals.
Existing runs from BL-022; new runs from this ticket (bold).

| run | start rounding -> kept | converged (residual) | volume L | CG y / z mm | IM3 R / L N | hinge R / L N | spreader pass-through |
|---|---|---|---|---|---|---|---|
| 23 in, `F_r1_PR23_fineFM` | 6 -> 2 mm | yes (0.41 N) | 82.4 | 135.7 / 486.8 | 457.4 / 522.2 | 181.6 / 192.3 | 0 nodes (4.6 mm) |
| **23 in, `F_r1_PR23_fineFM_sm8`** | **8 -> 4 mm** (3 mm hit max_iter) | yes (0.41 N) | 83.3 | **132.4 / 488.2** | **500.7 / 561.8** | 202.3 / 204.8 | 0 nodes (5.8 mm) |
| scatter 23 in | | | +0.9 | -3.3 / +1.4 | +9.5 % / +7.6 % | +11 % / +6.5 % | |
| 15 in guys off, `F_r1_PR15_fineFM_goff_sm8` | 8 -> 0 mm | yes (0.20 N) | 85.0 | 201.7 / 451.4 | 389.5 / 436.0 | 242.3 / 251.4 | 0 nodes (3.1 mm) |
| **15 in guys off, `F_r1_PR15_fineFM_goff`** | **6 -> 0 mm** | yes (0.27 N) | 85.2 | **201.3 / 451.0** | **387.4 / 449.6** | 241.4 / 253.9 | 0 nodes (3.0 mm) |
| scatter 15 in guys off | | | +0.1 | -0.4 / -0.4 | -0.5 % / +3.1 % | | |
| coarse guys off, `F_r1_PR15_goff_sm8` (BL-022) | 8 -> 2 mm | yes (0.41 N) | 87.5 | 186.6 / 445.5 | 911.4 / 970.4 | 972.6 / 904.4 | **56 nodes, 69.7 mm deep** |

Reading:
- **Guys-off IM3 is about 440–450 N at 1 g, not 970 N.** The two fine runs from different start roundings agree to
  3 % on IM3 and 0.4 mm on CG. The coarse 970 N run has part of the back panel tunnelled through the spreader (the
  penalty contact let 56 nodes through, up to 70 mm); its hinge loads (~900 N) and its 15 mm forward CG come from that
  tunnelled shape. It should be retired as a load basis (BL-021 checked the eye at it: 2911 N factored). The guys-off
  CG (201.3–201.7 mm) stands, so the "GUYS ON" carry rule from BL-022 stands.
- **23 in meat scatter is +/-4 % on IM3 about the mean of the two fine runs** (522 / 562 N; the rev 0 fine run gave
  518 N), 3.3 mm on CG y, 1.4 mm on CG z. The run that stopped earlier (kept 4 mm) carries more on the hooks and
  hinges, as the rounder field holds the bag a little further off the spreader. 561.8 N is just under the 15 in fine
  maximum (562.3 N) that BL-021 sized the IM3 eye on, so the eye envelope holds; the per-torso H1 body check at 23 in
  used 522 N and will see up to +7.6 % on the hooks and +6.5 % on the hinges if this run is taken as the basis.
- The H1 body's coarse/fine split (1.29 vs 1.00, BL-021) is **not** explained by this bug: BL-021 already evaluated
  the contact on the kept field. Its contact inputs differ little between meshes (15 in rev 1 meat spreader on the kept
  field: coarse 1067 N, fine 1116 N), so the split comes from where the loads land on the frame, not from their size.

ASSUMPTION SCATTER-23: the two fine 23 in meat runs bracket the fine-mesh answer. Settled by: a third fine run (10 mm
start) or, better, the 23 in prototype hook load cell test.

## 6. Reproduce

```
python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py run Fr0 --torso 15      # also 19, 23 (rev 0, ~2-3 min each)
python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py finerun F --torso 23 --cases meat --smooth 8 --tag _sm8
python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py finerun F --torso 15 --cases meat --guys off --tag _goff
python -m huntkit.clothsim.recontact outputs/clothsim/*/ outputs/clothsim/*/*/ --json designs/pack_5200/analysis/clothsim_contact_fix_results.json
python -m pytest -q tests/test_clothsim_contact_restore.py tests/test_clothsim_recontact.py tests/test_corrie_f_run_dirs.py tests/test_loadpath_check.py
```

## 7. Assumptions

- ASSUMPTION PT-25: a bag node more than 25 mm behind the spreader's bag-facing skin (inside its outline) has tunnelled
  through (penalty-contact failure), not deformed. Sound coarse runs reach 16 mm at the rim, the tunnelled run 70 mm.
  Settled by: none needed for the conclusion here (56 nodes vs 0); a contact solver with continuous collision
  detection would remove the need for the threshold.
