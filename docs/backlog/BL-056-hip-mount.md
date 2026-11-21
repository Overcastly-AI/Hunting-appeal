# BL-056 SLM Ti hip pivot mount base for the 8-insert pattern

**Agent:** structural-fea-engineer · **Size:** S

1. **Redraw** `designs/pack_5200/print/lug_hip_pivot_mount_slm_ti.stl` (today a 1.2 mm D44 disc with no screw holes) as a D50 × 3 mm base, with 8 × D5.5 holes at the positions in `analysis/h1_closeout.json`. Keep the legs and pivot, and keep ≥ 1 mm head-to-leg clearance. Check the base's own bending and the legs' joint to the base.
2. **Check the part fits the frame:** slice-check the base against the frame STL (screw access, head clearance, no clash). Export the STL and 3MF, with SLM notes (orientation and supports for a print service).
3. **Update the records:** add a superseded note to the `hipbelt_structural.md` §4 row. Update the ledger if the mass differs from the +13.8 g booked.
4. **Tests and full suite.** Don't edit the frame README / BUILD_H1, the kit or mfg; publish JSON.
