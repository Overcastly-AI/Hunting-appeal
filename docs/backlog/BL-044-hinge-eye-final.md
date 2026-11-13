# BL-044 Hinge eye on the new fairlead, and the bag-side loose ends

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-042, BL-043 · **Beside:** BL-045

1. **Hinge eye:** re-solve HE, its box and the B-01 stand-off against `bag_attach.HINGE_EYE_ENVELOPE`. That envelope is a 5.5 mm gap, a 20 mm throat, the pin 10.1 mm above the stay, and the cleat tip 17.7 mm proud. Switch `he_geometry`, `concepts/corrie_f.py:537` and `huntkit/viz3d/attach.py` to it, and replace the test at `test_bl041_recheck_fixes.py:55`.
   - Fix M-3: no peel on the box top row, and the eye legs in line with the pull. If peel can't be avoided, add a rated test: extend SEW-F or PT-3 to the hinge box shape at about 625 N peak.
   - Fix m-1: the HE-FIT band must agree with the cheek clearance.
   - Fix m-11 and n-6: the B-18 label overprinting the HE box.
   - Use the BL-042 test piece `print/frame_h1/test_pieces/hefit_hinge_fairlead_R` in HE-FIT, and check the eye on that STL geometry by slicing it.
2. **K-W keeper loops:** they are fixed at z 702.6, so W3 kinks at other torso settings. Re-place or re-shape them so W3 runs straight at every kit end, or justify keeping them.
3. **RT strap stand-off vs rifle barrel:** check it, then record or fix.
4. **Stale text:** the "hose ports at the collar seam" text in corrie.py, build_geometry.py and corrie_loadout.py. The notch moved onto a hem-ring notch on the L side. The test-kit screenshot names.
5. **Hinge pin:** about 2 mm longer (20 mm throat), BOM and spec.
6. **Weights:** regenerate the weight roll-up and mass docs (H1F +37.2 g).
7. **Renders:** re-render the rev 3 hero and side shots so they show the current clip, hose, B-25 and W3. Prefix `20261113_BL044_`.
8. **Release:** regenerate it and the kit, run the full suite, and add a test per finding. The release may say "ready to cut" only after a fourth independent review, so leave it at NOT ready.
