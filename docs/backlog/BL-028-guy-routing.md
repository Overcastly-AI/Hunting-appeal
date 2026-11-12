# BL-028 Guy routing on CORRIE F rev 1: real path, lifter clearance, CG

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-022, BL-026

## Why
BL-022 moved the guys to x ±52 on a B-25 bridle to clear the lifters, analysing the guy as a straight line to B-22 (244 mm). BL-026's 3D model shows that with a full bag the straight line runs through the bag. The real path runs outboard along the bar, round the crown corner and over the bag's top side corner (363–375 mm), and there it crosses the lifter band (x 91–119).

## Tasks
1. Model the guy's real path: wrap round the bar and over the bag corner, on the fine cloth drape at 15/19/23 in, full and 6-day loads. Report the length, angle, friction share, the force it delivers to B-22, and clearance to the lifter webbing at every crown kit.
2. If it clashes or loses effectiveness, design the fix. Options:
   - a guide loop or channel on the bag's top corner that keeps the guy inboard of the lifters;
   - moving B-22 so the straight path clears the bag;
   - routing the guy under the lifter with a sleeve;
   - another option.
   Re-run the 15 in meat CG (fine mesh) and R-28 with the fix.
3. Update `corrie_f.py` as rev 2 if anything changes (rev 1 reproducible), `corrie_f_body.md`, tests, and a diagram screenshot.

## Acceptance
- Guy and lifter webbing ≥ 10 mm apart at every crown kit, on the real path.
- 15 in meat CG ≤ 180 mm on the fine mesh.
- R-28 ≥ 31°.
