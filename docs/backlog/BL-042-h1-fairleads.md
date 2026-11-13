# BL-042 H1 print files: complete fairleads and hinge pin clearance

**Agent:** structural-fea-engineer · **Size:** M

Source: `designs/pack_5200/analysis/review_20261113_rev3_third.md`, Z-1 and Z-2.

1. **Z-2:** `h1_assembled.stl` and the two print halves clip every fairlead at y 15.46 (the envelope void in `frame_topopt.py:157`). The "fairleads present" check in `frame_h1.py:313` skips clipped voxels. Fix the export so every fairlead (hinge, IM1–3, US1–2, and any others) is complete, with its pin hole and walls. Replace the check with a real geometric one: for each fairlead, slice the STL through the pin axis and assert pin hole, throat and walls against the design. Regenerate `designs/pack_5200/print/frame_h1/`, keeping the halves watertight and the masses booked. Confirm the 28 mm IM3 cheek is still there. Check that no structural check depended on the clipped geometry, and re-run anything that did.
2. **Z-1, hinge fairlead clearance:** the fairlead floor under the pin (`bag_attach.py:87`) leaves 1.9 mm, but the webbing eye passing round the pin is 2–3 plies of 1.5 mm webbing. Set the hinge fairlead geometry so a 3-ply eye (4.5 mm), with margin, wraps the pin, and the throat passes the neck with stated clearance (the test currently asserts 18 mm in an 18 mm throat, i.e. zero). Keep the cheek strength (re-run the fairlead and cheek checks used in BL-024/027). Write the eye envelope the bag must meet (pin height, gap, throat) into a constant the pattern module can import.
3. **HE-FIT and IM3-EC print files:** both tests say to print "from the H1 STL". Export standalone test pieces (hinge fairlead and IM3 cheek) from the fixed geometry, and point the test kit at them.
4. **Tests and summary:** add tests and run the full suite. Write `designs/pack_5200/analysis/h1_fairleads.md`. Screenshots: sliced fairleads before and after, prefix `20261113_BL042_`.

Don't edit `patterns_corrie_f_rev3*.py`, because a pack-designer is working there. Expose the eye-envelope constant instead.
