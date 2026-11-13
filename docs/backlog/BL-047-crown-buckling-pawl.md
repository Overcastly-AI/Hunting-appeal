# BL-047 Crown frame buckling with the real top-bar offset; pawl pivot and window

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-046

1. **Crown buckling:** the real crown has the top bar 25 mm aft of the legs' plane and 32 mm corner dog-legs. On it, hipbelt-off abuse gives linear eigen-buckling of 0.54–0.57 (`h1_spine_channel.md`).
   - **Run (a) first:** a geometric non-linear (large-displacement) analysis with follower strap loads and realistic shoulder/lifter springs, with imperfections seeded from the first mode. Report the load–displacement path and the margin to limit load against HA-LS-1.
   - **If (a) does not give ≥ 1.0:** size the lightest fix. Compare (c), stiffer corner wraps or dog-legs, against (b), the top bar in the legs' plane. For (b), report its effect on R-28 head clearance and the clamp. Pick one and re-run every R1 check on the result.
   - **Define T1(c):** the hipbelt-off frame test, with sway measurement and pass criteria, in the test kit.
2. **Pawl:** the H1 print has no 8 mm pivot bore, although PRODUCTION.md op 2 reams one. The FDM pawl's tang and cord eye stand 13.5–14 mm off the tooth face, against a 9.3 mm zone. Add the bore and a window in the fore wall, and check the wall and housing strength. Slice-check the print through full pawl rotation, then re-export.
3. **Keep-outs:** re-base the old voxel keep-out masks on the new channel.
4. **Clamp web:** take the 2.0 mm web (−g) only if every margin holds.
5. **Ledger, records and full suite.** Screenshots prefix `20261113_BL047_`.
