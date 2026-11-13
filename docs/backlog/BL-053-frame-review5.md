# BL-053 Frame fixes from review 5

**Agent:** structural-fea-engineer · **Size:** L · **Beside:** BL-054

Source: `designs/pack_5200/analysis/review_20261113_fifth.md`.

1. **B-1, printability:** choose a print orientation per half and per test piece that keeps the layer direction the FEA assumed. Generate the support plan (tree supports in PAHT-CF, or a breakaway interface) and estimate filament and time. Check whether support scars land on fatigue-critical faces (the stays' wearer face, the fairlead roots); if so, re-orient or add a machining or sanding allowance and say so. Publish the print settings as data (JSON) that BL-054 turns into the README.
2. **M-1, cradle direction:** apply the cradle force with its real x component, legs inboard per the lane geometry. Run the eye-on-inner-cheek mechanism at US1/US2, the same check that failed the hinge before BL-049, and make MT-1cr's pull direction match the governing vector.
3. **M-2, nut traps:** give the US2 clevis a real hex nut pocket (as the z 234 joint has), with wall ≥ 2 mm. Re-check the joint.
4. **M-3, belly:** strengthen the US1 root and the US2 clevis or lug so the cradle passes strength ≥ 1.5 and fatigue ≥ 1.15 down to a 40 mm belly, or the flattest the straps can physically reach. The belly then stops being a safety rule. Report the mass.
5. **M-4, gauge pass values:** publish the root stress (MPa) per gauge location per load step for T1, MT-1cr and CLEVIS-SHARE. Update the CLEVIS-SHARE loads to the governing rows.
6. **M-5, pin retention:** design the retention for all 12 fairlead pins and the hinge pins, with parts, sources, hand removal for bag-off, and a test. Retention must not loosen under vibration.
7. **M-6, strap route:** model each strap's wrap over its own fairlead lip and the clevis block (contact, bend radius, abrasion). Carry the load the wrap puts on the clevis block in the joint check. Use `designs/pack_5200/us_route.py`; you may edit it.
8. **Finish:** re-export, slice-check, update the ledger and run the full suite. Don't edit `print/frame_h1/README.md` (BL-054 owns it); publish the data instead.
