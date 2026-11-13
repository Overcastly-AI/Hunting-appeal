# T1(c) hipbelt-off frame test, with sway measurement (BL-047)

Owner: structural-fea-engineer, 2026-11-13, BL-047. It is T1 variant (c) of `analysis/load_standard.md` §5.3 (HA-LS-1
rev C C8, 150 lb x 1.5 = **225 lb / 102 kg**, hipbelt unbuckled), with gauges added to settle the crown's buckling
question (`analysis/crown_gnl.md`). Register row to add (orchestrator / manufacturing-engineer): **T1c-SW**, phase 4,
kit C + D, after T1(a)/(b) on P2. Units: N, kg, mm; lb and in in brackets. Crane scale reads kg: N = kg x 9.81.

## Why

The linear eigen check of the real crown (top bar 25 mm aft, 32 mm corner dog-legs) gives 0.54 in hipbelt-off abuse.
The geometric non-linear analysis with real straps and the lumbar pad on the back finds no buckling up to 2.0 x the
225 lb load (margin >= 1.33). This test checks the non-linear model: the frame must hang without a growing sideways
sway of the stay feet (the 0.54 mode).

## Set-up (the T1 rig, `load_standard.md` §5.1)

1. Crown kit L at 23 in (the analysis' worst setting; run kit S at 15 in too if you have it). Bag on, 225 lb in
   25 % steps (56 / 112 / 169 / 225 lb) of sandbags in the bag, as for T1(a).
2. Hipbelt **unbuckled**. Lumbar pad resting on the hip log (as the wearer's back). Shoulder straps over the shoulder
   bar, lower strap adjusters snug, sternum strap off. Lifters snug (not cinched) for run 1; cinched hard for run 2.
3. Gauges:
   - **D1, D2:** dial gauges (0-25 mm) on the left and right stay feet, reading **fore-aft** (y), on magnetic bases
     on the rig floor.
   - **D3:** dial gauge on the crown top bar at its centre, reading **sideways** (x).
   - **D4:** the T1 crown-top reading (fore-aft), as in T1.
   - **S1, S2:** crane scales in series with the left lifter and the left lower shoulder-strap adjuster.
   - Phone photo, square to the side, at 225 lb: strap and lifter angles (ASSUMPTION STRAP-GEOM).

## Procedure

1. Zero the gauges with the empty pack hanging (bag on).
2. Load in 25 % steps; hold 1 min per step; at each step read D1-D4, S1, S2.
3. Hold 225 lb for **2 min**. Read again at the end of the hold.
4. Unload in the same steps. Read at 0.
5. Repeat for run 2 (lifters cinched).
6. **T1(c)-sway variant (150 lb only, optional):** lift the pack 50 mm off the hip log so it hangs free (no back
   contact) and repeat steps 1-4 to 150 lb. Never take the free-hanging pack above 150 lb.

## Results to record

For each step: load (lb), D1, D2, D3, D4, S1, S2. Then compute:
- **Sway** = |D1 - D2| / 2 (the antisymmetric fore-aft motion of the stay feet).
- **Southwell plot:** sway / load against sway for the steps above 50 % load. Fit a straight line; P_cr = 1 / slope.

## Pass criteria

| check | pass | prediction (`crown_gnl.md` §3) |
|---|---|---|
| T1 rules (crack, tap, crown set <= 1 mm, crown slip 0 teeth, no whitening at the pawl bushing or the upper bar) | as T1 | - |
| sway at 225 lb | **<= 3 mm** | <= 1.5 mm (4 mm imperfection) |
| sway after unloading | returns within **0.5 mm** of the zero | elastic |
| sway grows no faster than load | sway(225) <= 2.5 x sway(112) | about 1.5 x |
| Southwell P_cr (if the sway is readable, > 0.3 mm) | **>= 340 lb** (1.5 x 225 lb: HA-LS-1 buckling rule) | no limit below 450 lb |
| D3 crown sideways at 225 lb | <= 3 mm | < 1 mm |
| S1 lifter tension at 225 lb | record (settles LIFT-T) | 0-270 N |
| S2 lower strap tension at 225 lb | record (settles STRAP-SLING) | about 450-680 N |
| D4 crown-top sag against load | record the secant stiffness (settles STRAP-K) | - |

**If it fails** (sway over 3 mm, or Southwell below 340 lb): stop, send the log. The fix on file is stiffer corner
wraps or the top bar in the legs' plane (`crown_gnl.md` Summary; not sized, because the analysis did not need it).

## Safety

Back-up sling under the load, nobody under the pack, safety glasses. The free-hanging variant only to 150 lb.
