# BL-048 Fourth review fixes, bag side

**Agent:** pack-designer · **Size:** M · **Beside:** BL-047 (frame)

Source: `designs/pack_5200/analysis/review_20261113_rev3_fourth.md`.

1. **N-1, under-strap route:**
   - Model the real US1/US2 strap path in bag-on meat carry: cam-tight at 444 N, wrapping the loaded bag shape (cloth-sim fine mesh, as BL-028/029 did for guys). Report its contact with B-01, the hinge fairlead cheeks, the HE legs and box, and US1 (for US2).
   - Then fix it with a bag-side guide or channel on B-01, outboard of the hinge fairlead, keeping the strap ≥ 10 mm off the HE box and fairlead at every kit/torso end. Rate the guide.
   - If no bag-side guide can clear, say so with numbers and specify the US station move needed; BL-047 does the frame side.
   - Give HE-FIT step 0 a pass criterion. Export a US test piece (stay z 40–160) from the STL so the gate doesn't wait for P1 (ask BL-047 via your report if print edits are needed).
2. **M-B, webbing thickness:** specify the 38 mm webbing thickness (≤ 1.6 mm ply) in the BOM, the shopping list and the material record. Use one thickness consistently in the HE and B-25 code, and give a fallback if the bought roll is thicker.
3. **M-C, fixture pin:** specify a hardened steel 5 × 40 dowel for the PT-3/SEW-F fixture, and fix the shopping list. Make the hinge-row load one number across the bag (1019 N) and the frame pin check, and flag it for BL-047.
4. **M-A, TL-1:** update the TL-1 text and the release gate to BL-045's record (497 N, 57° below horizontal, 14 % outboard, spine end anchored). Update again if BL-047's crown re-run changes it.
5. **Minors:** m-2 to m-9. m-1 (frame-side fillet relief) is BL-047's.
6. **Release:** regenerate it and the kit, and run the full suite. The release still says NOT ready to cut; the fifth review decides.
