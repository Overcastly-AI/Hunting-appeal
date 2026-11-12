# BL-027 H1 buckling on the cloth-sim loads

**Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-024

## Why
On the CORRIE F cloth-sim loads, H1's Euler buckling check gives **0.43** (mid bar, hipbelt-off abuse, 23 in meat) and 0.71 (upper branch R, side-hill). On the beam loads it is 1.31. BL-024's adopted body H1-G0.55 is still 0.43. This blocks frame release R1. See `designs/pack_5200/analysis/h1_sleeve.md` "Found, not fixed".

## Tasks
1. **Is the load real?** Check whether the sim's sideways and axial loads on the mid bar and upper branches are real or an artefact of how BL-021 maps sim forces onto the frame: the leftover force and moment closure at the payload CG, and contact forces on the stays. Compare with the beam load set member by member.
2. **Size the fix.** Size the members on H1-G0.55 so buckling is ≥ 1.0 on the governing sim case and on the beam (target ≥ 1.2 for the hipbelt-off abuse case if cheap). Keep fatigue ≥ 1.15 and every interface. A hand estimate says about +17 g (mid bar to about 108 mm², upper branches to about 128 mm²); verify it with the voxel or beam model, not by hand.
3. **Fix the label.** Correct `frame_cg_recheck.region_label` so it names the region where the governing voxels actually are (additive or a fix with a test).
4. **Print files.** If the result passes, write the updated H1 print files (`designs/pack_5200/print/frame_h1/`). Include the 28 mm IM3 cheek. Make sure each flat half is one clean closed shell, with the loose island and slivers BL-015 found removed. Update the README and `frame_h1.md` §7 release list.

## Deliverables
`huntkit/gendesign/h1_buckling.py`, `tests/test_h1_buckling.py`, `designs/pack_5200/analysis/h1_buckling.md`, updated print files if passing, and screenshots `outputs/screens/20261112_BL027_*.png`.
