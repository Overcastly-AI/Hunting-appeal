# H1 stay crown restored at the old US stub sites (BL-051)

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-051-stay-crown.md`. Code `huntkit/gendesign/h1_crown.py` (`python -m huntkit.gendesign.h1_crown --lug | --body`; the report with no flag); fix in `h1_lanes.strip_old_us` (`CROWN_RESTORE`, `_crown_bridge`); lug FEA option `h1_lanes.lug_fea(stay_poly=)`; spreader rule `spreader.us2_notch_check` (`proud_mm`); tests `tests/test_h1_crown.py`. Results `h1_crown.json`. Units mm, N, g (imperial in brackets). Supersedes the print, slice, notch and lug numbers of `h1_bedfit.md` and `h1_lanes.md` where they differ.

## Summary

- **Cause found:** `h1_lanes.strip_old_us` (BL-049) removed every voxel outside the stay *circle* (r 9 + 1 mm) inside the old US1 / US2 fairlead footprints. The H1 stay is fuller than that circle on the bag face (plain crown on the stay axis y 9.82 R / 9.66 L), so its crown went with the stub: on the BL-050 print the axis crown sat at y 7.67 (z 137), 2.15 mm low, and **3.13 mm** on the worst line (x +118; L 2.63 mm), over z 131-152 and also over z 86-104 at the old US1 site.
- **Fixed at the source:** `CROWN_RESTORE` bridges the stay section across each strip zone (the plain stay sections 4-8 mm beyond each end, intersected). Re-exported: crown continuity on x = +/-112, 115, 118 over z 92-152: worst drop **0.29 mm**, worst 1 mm step 0.45 mm (rule <= 0.5 / 1.0): **pass True**. New test `test_crown_is_continuous`.
- **Print:** assembled 997.7 g (+2.6 g against BL-050 995.1), lower 425.9 g, upper 543.5 g, clevises 14.14 g, 14.14 g; lower footprint [321.05, 299.58, 76.7] at 163.5 deg, brim spare [2.95, 4.42] mm (unchanged). Every file one closed shell.
- **Slice checks** pass: fairleads True (12 / 12), spine channel True, pawl True, test pieces True; US2 joint slices True. **us_route** print_lanes worst US1 12.4 / US2 14.6 mm (>= 10): pass True.
- **US2 clevis joint** (geometry unchanged, re-run): strength 3.85 (net_section, cradle), fatigue 1.73 (net_section_paht); share 1.0: 2.31 / 1.04.
- **US2 lug** on the real stay section (crown in): strength **2.93**, fatigue **1.32** (root 1.37, arm 1.32); the r 9 circle stub of BL-049 / BL-050 gave 2.31 / 1.04.
- **Body** (h1_buckling.full_check, 4 bases, lane loads): strength 1.61 (was 1.61), fatigue 0.83 (was 0.83; fine_sm8.cyc, the BL-024 cinch-cycled set below 1 since BL-024, R1 hold for MT-1, not this ticket; the other bases 1.24), buckling 1.09 (was 1.11), z 234 joint 1.96 / 1.09. Bag-off cradle: 2.56 / 1.15 / buckling 5.10 (was 2.54 / 1.14 / 5.14).
- **US1 root (item 2): the stub model governs, fatigue 0.86** on the real stay section (0.80 on the circle stub); the whole body reads 1.153 because it never puts the pin load through the arm. **Below 1.0: target not met** (section 4). The T1 strain-gauge text is not in the kit; the change is listed for BL-050B (section 4).
- **Spreader z 142 notch:** BL-050's '2.31 mm air' was the cut-away crown. With the crown back, the notch footprint holds the plain crown, 0.17 mm under the support line (old 1.5 mm air rule: False). Rule now: nothing proud of the support line (proud -0.17 mm <= 0.0): pass True. Closing the notch is now the natural option (owner).
- **Cleanup, n_pin (not done as written, on purpose):** of the 12 stations, `bag_attach._mass_budget` books 8 pins + sleeves and `meat_haul.cradle_parts_g` already books the US1 / US2 four ('under-straps US1/US2: 7075 pins (4)', 'UHMWPE sleeves (4)' = 10.8 g; CORRIE F books them in its 'US-anchor ... (frame side)' row). Setting n_pin to 12 would have booked them twice, and so did BL-050's '+10.80 g, 4 stations booked short' ledger row. Fixed at the source by making the count explicit (`bag_attach._pins_booked_here`, `CRADLE_PIN_STATIONS`) and retiring the BL050 row: **-10.8 g** on every config. `h1_lanes.md / .json` carry a superseded note; screws and washers have distinct BOM IDs and callouts (section 6).

## 1. Cause and fix

`strip_old_us` takes the old US1 / US2 fairlead stubs off the voxel body before the print mesh and the body FEA (BL-049). Its keep rule was 'inside the stay circle (r + 1 mm)'. On the H1 body the stay is not that circle: on the bag face it is a crown about 3 mm fuller (sections at z 116 / 122: 344.8 / 381.6 mm2 against the circle's 265.2 / 252.4 mm2). Over z 138-146 the release body had no crown either (the old stub's throat). `CROWN_RESTORE` now sets every voxel of each strip zone solid where the body is solid at the same (x, y) on all reference planes 2-4 voxels (4-8 mm) beyond both ends of the zone (1 voxel out still carries the old stub's edge blend: y 11 at z 103-107, which made a 1.5 mm hump in a first try). The restored stay is never fuller than the leaner side. The same function feeds the body FEA (`h1_lanes.body_solid`), so the FEA body and the print agree.

| line | rule | BL-050 print: min y (z) / drop / max step | BL-051 print: min y (z) / drop / max step | pass |
|---|---|---|---|---|
| x +112 | ref 8.85 | 6.89 (141) / 1.95 / 0.77 | 8.8 (144) / 0.04 / 0.22 | True |
| x +115 | ref 9.82 | 7.67 (137) / 2.15 / 0.99 | 9.8 (92) / 0.02 / 0.32 | True |
| x +118 | ref 9.88 | 6.76 (141) / 3.13 / 1.82 | 9.6 (92) / 0.29 / 0.45 | True |
| x -112 | ref 8.02 | 6.39 (138) / 1.64 / 1.02 | 7.92 (114) / 0.11 / 0.35 | True |
| x -115 | ref 9.66 | 7.59 (137) / 2.06 / 0.83 | 9.65 (96) / 0.01 / 0.18 | True |
| x -118 | ref 9.9 | 7.24 (142) / 2.63 / 1.4 | 9.77 (92) / 0.13 / 0.39 | True |

Residual: a 0.3-0.4 mm bump at z 104-108 (the old US1 stub's upper edge blend, outside the strip zone, in the print since BL-045) and the hinge throat's lead-out at z 88-91 (1 mm below the crown, part of the BL-049 hinge throat, not the crown).

## 2. Print files and slice checks

| file | g (BL-050) | g (BL-051) | watertight / shells | footprint mm |
|---|---:|---:|---|---|
| h1_assembled.stl | 995.1 | 997.7 | True / 1 | |
| h1_lower_flat.stl | 423.4 | 425.9 | True / 1 | [321.1, 299.6, 76.7] (rot 163.5, brim spare [2.95, 4.42]) |
| h1_upper_flat.stl | 543.5 | 543.5 | True / 1 | [309.4, 280.1, 64.4] (rot 90.0, brim spare [14.61, 23.88]) |
| test_pieces/us_route_stay_R.stl | 125.9 | 127.1 (as assembled 141.3) | True / 1 | [117.0, 120.0, 64.7] |

Slice checks on `h1_assembled.stl` (`h1_lanes.slice_checks`): fairleads True, every one with its eye stack:

| station | gap under pin | throat | cheek | cheek height | pass |
|---|---:|---:|---:|---:|---|
| hinge_L | 6.49 | 20.0 | 9.99 | 35.98 | True |
| hinge_R | 6.5 | 20.0 | 9.99 | 35.97 | True |
| us1_L | 5.5 | 20.0 | 8.0 | 18.0 | True |
| us1_R | 5.5 | 20.0 | 8.0 | 18.0 | True |
| us2_L | 5.5 | 20.0 | 8.0 | 17.98 | True |
| us2_R | 5.5 | 20.0 | 8.0 | 17.98 | True |
| im1_L | 5.5 | 20.0 | 7.99 | 17.98 | True |
| im1_R | 5.5 | 20.0 | 7.99 | 17.98 | True |
| im2_L | 5.5 | 20.0 | 7.99 | 18.0 | True |
| im2_R | 5.5 | 20.0 | 7.99 | 17.98 | True |
| im3_L | 5.5 | 20.0 | 7.98 | 27.99 | True |
| im3_R | 5.5 | 20.0 | 7.98 | 27.99 | True |

Spine channel clear 0.964 mm: True; pawl swing: True; test pieces: us_route_stay_R|hinge_R True, us_route_stay_R|us1_R True, us_route_stay_R|us2_R True, hefit_hinge_fairlead_R|hinge_R True, im3ec_cheek_R|im3_R True. US2 joint slices (`h1_bedfit.joint_slices`): True.

## 3. US2 lug, joint, strap route, spreader notch

Lug FEA (`h1_lanes.lug_fea`, 1 mm voxels, every US load: cradle 720 N at 2.4, bag-on at 3.0, +/-10 deg fleet). BL-049 / BL-050 modelled the stay as the r 9 circle; the crown that is now printed is in the second model (the print's plain stay section next to the station, ASSUMPTION CROWN-SECTION). Lowest per region over the loads, fatigue (strength):

| lug | stay model | fairlead | arm | root | worst strength | worst fatigue |
|---|---|---|---|---|---:|---:|
| us1 | r 9 circle (BL-049) | 1.62 (3.59) | 1.19 (2.65) | 0.8 (1.78) | 1.78 | 0.8 |
| us1 | real section (BL-051) | 1.62 (3.59) | 1.2 (2.66) | 0.86 (1.91) | 1.91 | 0.86 |
| us2 | r 9 circle (BL-049) | 1.62 (3.61) | 1.38 (3.07) | 1.04 (2.31) | 2.31 | 1.04 |
| us2 | real section (BL-051) | 1.66 (3.7) | 1.32 (2.93) | 1.37 (3.03) | 2.93 | 1.32 |

US2 clevis joint (`h1_bedfit.joint_check`, geometry unchanged): share 0.6 strength 3.85, fatigue 1.73; share 1.0 2.31 / 1.04. Strap route (`us_route.py`, 'print_lanes', on the new STL): worst US1 12.4 / US2 14.6 mm, pass True.

Spreader z 142 notch (`spreader.us2_notch_check`): support line y 10.01 (z 127) to 11.84 (z 160); the print inside the notch footprint is the stay crown, 0.17 mm below that line at its closest. BL-050 measured 2.31 mm because the crown was cut away; the 1.5 mm 'root air' it passed was the defect. The arm root now blends into the stay under the crown and never reaches the sheet plane, and the crown is the sheet's support along the whole stay, so the rule is: nothing in the notch stands proud of the support line (proud -0.17 mm, pass True). The notch no longer clears anything (no cleat on the stay at z 142 since BL-049): closing it gives the sheet bearing there too (owner option, needs the spreader re-run).

## 4. Body, and the US1 root (item 2)

`h1_buckling.full_check` on the restored body (`h1_lanes.body_solid`, lane loads, real crown; cache `check_m1_u2.5_im3_bl051_crown`) against the BL-049 / BL-050 body (`check_m1_u2.5_im3_bl049_lanes`; BL-050 changed only the print, not the voxel body):

| basis | strength | fatigue | creep | buckling | z 234 joint strength / fatigue |
|---|---|---|---|---|---|
| fine_sm8 | 1.678 -> **1.679** | 1.247 -> **1.258** | 2.660 -> 2.683 | 1.171 -> **1.171** | 2.08 / 1.71 |
| fine | 1.678 -> **1.679** | 1.263 -> **1.271** | 2.694 -> 2.712 | 1.138 -> **1.138** | 2.08 / 1.71 |
| beam | 1.611 -> **1.613** | 1.223 -> **1.235** | 2.610 -> 2.635 | 1.250 -> **1.256** | 1.96 / 1.25 |
| fine_sm8.cyc | 1.678 -> **1.679** | 0.829 -> **0.834** | 1.768 -> 1.778 | 1.106 -> **1.095** | 2.11 / 1.09 |
| bag-off cradle (lanes) | 2.538 -> **2.563** | 1.142 -> **1.153** | 2.437 -> 2.460 | 5.138 -> **5.100** | |

Raster 888.9 -> 892.8 g. Governing fatigue region (fine_sm8): lumbar struts / pan / peak stay L lower sleeve z 160-240 (branch / strut root). The fatigue minimum of the cycled basis (fine_sm8.cyc, the BL-024 cinch-cycled set) has been below 1 since BL-024 (R1 hold for MT-1, h1_lanes.md section 3); the crown does not change it.

**Which US1 number governs.** Stub model 0.8 (circle) / **0.86** (real section, strength 1.91); whole body 1.153 (BL-049: 1.142). **The stub model governs.** The whole-body model applies each US pin load at the stay node (force + the lane moment, h1_lanes.lane_items): the arm carries no pin load there, so its root sees only the stay's global stress. The stub model routes the pin load through the cheeks and the arm into the root, which is what loads that root; its fixed stub ends leave out the lower branch (conservative) and the global stay stress (unconservative). The stub number is the one to design to until the T1 / MT-1 strain gauge at the US1 root settles it. So the US1 arm root fails the fatigue requirement (>= 1.0 at the 1.6 g walking peak, 1e5 cycles) by about 14 % on the best model there is, and the body number does not clear it. The fix is a design change, not this ticket: BL-049 proposal 2 (run the US1 arm onto the lower branch it touches, which also unblocks the lighter arms), or a taller root (the US1 arm spans z 90-106: it cannot go down, the hinge cheek top is z 87; upward it has up to 6 mm to the spreader sheet's bottom edge, z 112; neither is sized here). Until then the first article's T1 and MT-1 carry a strain gauge at the US1 root.

**Kit text (for BL-050B; `physical_test_kit.py` is theirs and not edited here):** physical_test_kit.py, test T1 (and its TEST_PLAN / test_register rows): add 'strain gauges (1 mm foil, 120 ohm, quarter bridge, cyanoacrylate on the sanded PAHT) on the US1 arm root (R side, bag face, 3 mm off the stay surface, gauge axis along the arm) and on the US2 arm root (same place); record at 0 / 150 / 300 lb in T1 (a)/(b) and at 240 / 480 / 720 N per pin in the MT-1 cradle pull; PASS: measured root stress (strain x 3.86 GPa, youngs_modulus_xy_mpa of data/materials pa12_cf_fdm_paht) <= the h1_crown lug model's root stress at that load (ASSUMPTION US1-STUB-GOVERNS / STAY-STUB / CROWN-SECTION)'. The CLEVIS-SHARE pull's 'optional strain gauge at the US2 arm root' becomes required, same gauge place.

## 5. Mass

| item | g | oz |
|---|---:|---:|
| print: stay crown restored (assembled BL-051 997.7 - BL-050 995.1) | +2.6 | +0.09 |
| attachment: BL-050's US1 / US2 pins + sleeves row retired (double count with the cradle rows) | -10.8 | -0.38 |

Ledger row BL051 (`huntkit/mass/ledger.py`, from this json); the BL050 step drops by the retired 10.8 g (`analysis/weight_rollup_v2.json`). Printed: lower 425.9 g, upper 543.5 g, clevises 28.3 g (997.7 g, 2.20 lb). Lug arms as unioned 69.84 g (the union adds a little less than before: the crown now holds part of their root).

**Mass reductions that keep the SF (not applied):** the restored crown is +2.6 g and holds no margin that governs anywhere else; the US2 lug now has fatigue margin (root 1.37, arm 1.32 on the real section) that the circle model hid, so the US2 arm could taper further (not sized here: a lug FEA sweep on the real section would set it). The US1 arm cannot lose anything (0.86).

## 6. BOM mix-up (washers 10 / 12 mm, screws M5 x 40 / x 45)

Both joints use M5 Ti DIN 7984 screws and A2 washers that differ only in length / OD. The print README's shopping list now gives each its own BOM line and ID: **HW-J234-SCR** M5 x 45 (z 234 joint, 4), **HW-J234-WSH** 12 mm OD (z 234 joint, 8), **HW-US2-SCR** M5 x 40 (US2 clevis, 4), **HW-US2-WSH** 10 mm OD DIN 433 (US2 clevis, 8), **HW-M5-NUT** (both, 8), with a callout to bag and label them apart and the IDs in the assembly steps. Consequence of a swap: an M5 x 40 at z 234 does not reach through the nut; an M5 x 45 in the clevis bottoms in the blind tail hole (|x| 142.5) before the head seats; a 10 mm washer at z 234 loses the washer-bearing area the joint is sized on; a 12 mm washer does not fit the clevis block. The ledger's BL050 hardware row named the clevis screws 'M5 x 35' (a typo against `h1_bedfit.hardware_g`'s M5 x 40); it now prints the names from `h1_bedfit.hardware_g` with the BOM ID.

## 7. Assumptions

- ASSUMPTION CROWN-BRIDGE: The stay section over each old stub site is the intersection of the plain stay sections 4-8 mm beyond each end of the strip zone (h1_lanes._crown_bridge); what the topology body had under the old stub is unknown (the stub was a keep-in). Settled by: Not needed for strength (the FEA uses this body); first-article slice / caliper of the crown at z 96 and z 142 against z 122 (within 0.5 mm).
- ASSUMPTION CROWN-SECTION: The lug FEA's stay stub takes the print's plain stay section next to each station (US1 z 116, US2 z 122) in place of the r 9 circle; the stub still ends at +/-22-23 mm and leaves out the lower branch. Settled by: Strain gauge at the US1 and US2 arm roots in T1 (and the MT-1 cradle pull) on the first article.
- ASSUMPTION NOTCH-PROUD: The z 142 spreader notch now sits over a plain stay crown: the rule is that nothing in the notch footprint stands proud of the sheet's support line (BL-050's 1.5 mm air rule was measured on the cut crown). Settled by: Spreader dry fit on the first article: the sheet edge each side of the notch bears on the crown, no rocking.
- ASSUMPTION US1-STUB-GOVERNS: For the US1 arm root the stub model governs over the whole body (see section 4). Settled by: Strain gauge at the US1 arm root, T1 (a) / (b) and the MT-1 cradle pull: measured root strain x E / the stub model's root stress at the same load <= 1.0.
- ASSUMPTION Carried: CLEVIS-SHARE, CLEVIS-DRY, CLEVIS-PRINT, SEAM-FLOOR, HEAD-PROUD, BED-ROT (h1_bedfit.md 7); STAY-STUB, LANE-MOMENT, HINGE-ROW, FI99-RULE (h1_lanes.md 6); US-FLEET, US-TOPO, DRAPE-US (us_route.json). Settled by: as there

## 8. Screenshots

- `outputs/screens/20261113_BL051_1.png`
- `outputs/screens/20261113_BL051_2.png`
- `outputs/screens/20261113_BL051_3.png`
