# BL-059 Wire the BL-058 results into BUILD_H1, the test kit, the print README and the bag release

**Agent:** manufacturing-engineer · **Size:** S · **Depends on:** BL-058

Goal: no generated document carries pre-BL-058 values. Source: `designs/pack_5200/analysis/bl058.json` (`kit.nut`,
`kit.hip_screw`, `kit.pins_bom`, `kit.PIN-RET_d`, `kit.FIT-US_marks`, `kit.hip_guide`, `hip_mount`, `stl`, `mass`,
`head_check`, `sleeve_bearing`, `assumptions`), `h1_closeout.json pins` (BL-058 overlay) and `huntkit/mass/ledger.py`
(`bl056_update` + `bl058_update`). Numbers are read, never typed.

1. **Hip mount:** screws M5 x 12 (was x 14), 3 mm hex driver (was 4 mm key), holes D5.8, printed insert-setting guide
   `test_pieces/hip_insert_guide` (print it; start-then-finish; guide bore <= 7.4 mm, GUIDE-HEAT), INSERT-SET flush
   check, all 8 screws start by hand at first article (INSERT-SCATTER). Mount mass from the ledger (BL056 + BL058,
   checked against `hip_mount.mass_g`) and its slm_cost row.
2. **Retainers:** McMaster 90153A214 hairpin clips at hinge / US1 / IM (fallback 90153A216, clip body toward the
   wearer, D1.5 cross hole), US2 groove + DIN 6799 E-clip, US2 tether (180 mm, larks-head round the lug arm at |x| 132).
   No "R-clip / 699 N" text left (hairpin wire double shear 303 N). PIN-RET (d) row; FIT-US colour marks include the
   pin head, E-clip and tether. HW-PIN-RET split into HW-PIN-RET-H / -E (+ HW-PIN-TETH).
3. **US2 pin:** 7075-T6, shank 39.6 mm, head D8 x 1.0 in the D9 x 1.5 counterbore; US2 outer UHMWPE sleeve 6.5 mm.
4. **BOLT-LEN:** M5 x 35 caliper window 34.7-35.3 mm (BUILD_H1 8.2) and the M5 x 45 ISO 4759-1 window (7.2), next
   to the DIN 934 nut check.
5. **Masses:** clevis 15.67 g, assembled 1069.32 g (`mass_check` reads `bl058.json stl`); MASS-BAND regenerated.
6. **BL-057 tests:** the two red tests in `tests/test_bl057_wiring.py` read bl058.json / the ledger (intent kept).
7. **BL-057 leftovers:** TEST_PLAN row 18 and `hipbelt_structural.md` §8 HB-6 bullet regenerated from
   `hip_mount_bl056.json tests.HB-6`; HB-6b torque (sourced value = insert record tightening_torque_max_n_m 2.5 N m,
   BUILD_H1's 2.0 traced to no record); T1 US2 gauge lines re-run on the current print with the source function
   (`h1_rev5.gauge_values`, `tests_physical/t1_us2_gauge_bl059.json`, md5-locked to the STL); "96 h" = the JLC3DP Ti
   SLM service time of the cited cost source; `huntkit/gendesign/docs.write_print_readme` writes the build package's
   hip row for the PROTECTED mount (never the gendesign 20.2 g).
8. **Bag release README:** review-6 M-1, M-2, M-3, M-5, m-2, m-3, m-8 closed with BL-058 evidence (read from
   bl058.json); frame-kit BOM line carries the BL-058 retainers.

Deliverables: `designs/pack_5200/frame_h1_build.py`, `designs/pack_5200/physical_test_kit.py`,
`designs/pack_5200/mfg_corrie_f_rev3.py`, `huntkit/gendesign/docs.py`, `tests/test_bl059_wiring.py` (+ stale
assertions in `tests/test_bl057_wiring.py`, `tests/test_frame_h1_build.py`), regenerated `print/frame_h1/README.md`,
`BUILD_H1.md`, `print/README.md`, `tests_physical/test_register.csv`, `TEST_PLAN.md`, `t1_us2_gauge_bl059.json`,
`analysis/hipbelt_structural.md` (HB-6 bullet), `outputs/release/test_kit/`, `outputs/release/pack5200_corrie_f_rev3/`.
Screenshots `outputs/screens/20261121_BL059_<n>.png`. Do not commit.

Check: `python designs/pack_5200/mfg_corrie_f_rev3.py --check`; full suite.
