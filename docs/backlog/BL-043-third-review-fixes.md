# BL-043 Third review fixes (bag side, except the hinge eye)

**Agent:** pack-designer · **Size:** M · **Beside:** BL-042

Source: `designs/pack_5200/analysis/review_20261113_rev3_third.md`.

1. **M-1:** W3 is anchored to the crown bar, so its path moves with torso and kit (z 601 to 741). Make the W3 routing, the W3G guide and the roll clip work at every kit and torso end: check S/M/L at both ends, with ≥ 10 mm clearance, and keep loads off unrated tacks. Test all six corners.
2. **M-2:** model the moved roll-clip strap origin and tab on the cloth-pass roll model (as BL-031/BL-020 did), and re-derive the RT cut. Fall back to the old origin if the new one tucks in.
3. **M-4:**
   - Draw the 38 mm B-25 topology: sleeve, 90° turn, tab and spine wrap, with a real spine-clamp width from the frame files.
   - Check the spine wrap.
   - Make TL-1's specimen include the real turn, so it proves the 38 mm bearing.
4. **Minors:** do all 14 except those tied to the hinge eye (the HE-FIT band, the n-6 label over the HE box), which wait for BL-042. That includes:
   - IMC raw-end length;
   - thread hardware before op 7.13;
   - TL-1 gauge location;
   - 1.28 m crown bar stock;
   - W3 vs the hose slot;
   - camo print BOM quantity;
   - per-step machine/needle/thread on ops 4.05 and 4.08;
   - n-7 webbing pages (labels; add B-25 and RT).
5. **Afterwards:** regenerate the release and kit, and run the full suite. Write a regression test for each finding. Do not touch the HE/hinge geometry; BL-044 does that after BL-042.
