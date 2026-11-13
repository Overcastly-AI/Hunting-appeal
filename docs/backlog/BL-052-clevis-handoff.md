# BL-052 Clevis hardware, kit text and belly mark (handoff from BL-051)

**Agent:** pack-designer · **Size:** S · **Depends on:** BL-051

The full wording is in `designs/pack_5200/analysis/h1_crown.md` §4.

1. `mfg_corrie_f_rev3.frame_bolt_lines`: clevis washers become `n_cl * BF.JOINT.n_washers` (4); bolts M5 × 35 from `BF.JOINT`. Regenerate the release BOM and the test kit.
2. Kit text:
   - US-route and CLEVIS-SHARE steps: M5 × 35, no head washer, 2 × 10 mm washers on the nut side;
   - strain gauges at the US1/US2 arm roots in T1 and MT-1;
   - record the cradle belly in MT-1;
   - make the CLEVIS-SHARE gauge required.
3. **Minimum cradle belly 60 mm** (orchestrator call): add a sewn strap mark or gauge on the US straps and a line in the meat-haul instructions and user guide. Book any mass.
4. **Clevis face contact:** add an inspection step after FIT-US / T9 for wear on the bag side panel at z 127–157.
5. Update `tests/test_bl050b_bag_lanes.py` for the counterbored joint and the regenerated release. Run the full suite.
