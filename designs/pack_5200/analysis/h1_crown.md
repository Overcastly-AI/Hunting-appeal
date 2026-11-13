# H1 stay crown restored at the old US stub sites (BL-051)

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-051-stay-crown.md`. Code `huntkit/gendesign/h1_crown.py` (`python -m huntkit.gendesign.h1_crown --lug | --body`; the report with no flag); fix in `h1_lanes.strip_old_us` (`CROWN_RESTORE`, `_crown_bridge`); lug FEA option `h1_lanes.lug_fea(stay_poly=)`; spreader rule `spreader.us2_notch_check` (`proud_mm`); tests `tests/test_h1_crown.py`. Results `h1_crown.json`. Units mm, N, g (imperial in brackets). Supersedes the print, slice, notch and lug numbers of `h1_bedfit.md` and `h1_lanes.md` where they differ.

## Summary

- **Cause found:** `h1_lanes.strip_old_us` (BL-049) removed every voxel outside the stay *circle* (r 9 + 1 mm) inside the old US1 / US2 fairlead footprints. The H1 stay is fuller than that circle on the bag face (plain crown on the stay axis y 9.82 R / 9.66 L), so its crown went with the stub: on the BL-050 print the axis crown sat at y 7.67 (z 137), 2.15 mm low, and **3.13 mm** on the worst line (x +118; L 2.63 mm), over z 131-152 and also over z 86-104 at the old US1 site.
- **Fixed at the source:** `CROWN_RESTORE` bridges the stay section across each strip zone (the plain stay sections 4-8 mm beyond each end, intersected). Re-exported: crown continuity on x = +/-112, 115, 118 over z 92-152: worst drop **0.29 mm**, worst 1 mm step 0.45 mm (rule <= 0.5 / 1.0): **pass True**. New test `test_crown_is_continuous`.
- **Print:** assembled 996.6 g (+1.5 g against BL-050 995.1), lower 425.6 g, upper 543.5 g, clevises 13.76 g, 13.76 g; lower footprint [321.05, 299.58, 76.7] at 163.5 deg, brim spare [2.95, 4.42] mm (unchanged). Every file one closed shell.
- **Slice checks** pass: fairleads True (12 / 12), spine channel True, pawl True, test pieces True; US2 joint slices True. **us_route** print_lanes worst US1 12.4 / US2 14.6 mm (>= 10): pass True.
- **US2 clevis heads counterbored (orchestrator item 1):** each head now sits in a 9 mm counterbore 4 mm deep, 0.5 mm below the clevis outer face (|x| 183.0), bearing on the PAHT with no washer; bolt axes 1.5 mm higher (dy -2.8) for a 2.5 mm wall; screws **M5 x 35** (were M5 x 40), 4 washers (were 8). Nothing stands proud of the clevis now. But the free drapes (no frame in the sim) pass **4.0 mm inside the clevis's flat outer face** (the US2 outer cheek face, there since BL-049) on all 12 drapes: the bag panel will rest on that face whatever the heads do. **The >= 3 mm clearance is not met by the clevis face** (owner / pack-designer item, section 3a).
- **US2 clevis joint** (recessed heads; every cradle row incl. the lane rows): strength 3.11 (net_section, cradle_lane_b50), fatigue 1.4 (net_section_paht); share 1.0 (sensitivity): 1.87 / 0.84 (below 1 only at the 50 mm belly row).
- **US2 lug, real leg angle (orchestrator item 2):** on the lane the cradle leg is 23.0 deg at the 70 mm design belly (638.8 N): strength 3.34, fatigue 1.5; at a 50 mm belly 16.9 deg, **860.2 N: 2.5 / 1.13** (governs; real stay section). The 720 N row at 31.3 deg: 2.93 / 1.32. On the r 9 circle stub of BL-049 / BL-050 the 860 N row would read 1.82 / 0.82: the crown is what carries it.
- **Body** (h1_buckling.full_check, 4 bases, lane loads): strength 1.61 (was 1.61), fatigue 0.83 (was 0.83; fine_sm8.cyc, the BL-024 cinch-cycled set below 1 since BL-024, R1 hold for MT-1, not this ticket; the other bases 1.24), buckling 1.09 (was 1.11), z 234 joint 1.96 / 1.09. Bag-off cradle: 2.56 / 1.15 / buckling 5.10 (was 2.54 / 1.14 / 5.14); on the lane (new, per-strap angle and tension): 70 mm belly 2.66 / 1.20 / buckling 1.90, 50 mm belly 2.38 / 1.07 / buckling 1.31.
- **US1 root (ticket item 2): the stub model governs** (the whole body never routes the pin load through the arm). At the loads the lane really sees, real stay section: design belly 70 mm (529.3 N, 45 deg) fatigue **1.09**; 50 mm belly (643.8 N) **0.95**; 1.00 at 55 mm, 1.03 at 60 mm. The 0.80 / 0.86 quoted before is the 720 N envelope at 31.3 deg, which no lane cradle reaches at US1. **Target met at the design belly, not below a 55 mm belly**: the meat-haul instruction needs a minimum belly (owner decision; 60 mm proposed). Whole body: 1.153. The T1 strain-gauge text is not in the kit; the change is listed for the kit owner (section 4).
- **Spreader z 142 notch:** BL-050's '2.31 mm air' was the cut-away crown. With the crown back, the notch footprint holds the plain crown, 0.17 mm under the support line (old 1.5 mm air rule: False). Rule now: nothing proud of the support line (proud -0.17 mm <= 0.0): pass True. Closing the notch is now the natural option (owner).
- **Cleanup, n_pin (not done as written, on purpose):** of the 12 stations, `bag_attach._mass_budget` books 8 pins + sleeves and `meat_haul.cradle_parts_g` already books the US1 / US2 four ('under-straps US1/US2: 7075 pins (4)', 'UHMWPE sleeves (4)' = 10.8 g; CORRIE F books them in its 'US-anchor ... (frame side)' row). Setting n_pin to 12 would have booked them twice, and so did BL-050's '+10.80 g, 4 stations booked short' ledger row. Fixed at the source by making the count explicit (`bag_attach._pins_booked_here`, `CRADLE_PIN_STATIONS`) and retiring the BL050 row: **-10.8 g** on every config. `h1_lanes.md / .json` carry a superseded note; screws and washers have distinct BOM IDs and callouts (section 6).
- **meat_haul.py (orchestrator item 3):** HALF_SPAN_MM 115 kept as the LEGACY stay-x span with a comment (the 720 N envelope row, the cradle FEA and the bag-on resolution were booked at its 31.3 deg); new `lane_half_span` / `theta_lane` (US1 70 / US2 165 mm half spans = 140 / 330 spans: 45 / 23 deg); the lane rows now sit in `h1_lanes.lug_loads` ('cradle_lane', 'cradle_lane_b50'). '38 mm cams / 38 mm webbing 1.10 m': NOT changed, on purpose: `cradle_parts_g` is the CORRIE B.2 booking, the ledger's baseline that `strap_arch.today_parts` reads by name; CORRIE F removes those rows and books its own 25 mm cams (cam_25mm_al) and webbing (strap_arch rec). Re-massing them to 25 mm moved the B.2 baseline by -23.8 g and broke the roll-up (tried, reverted); the docstring now says so. The bag-on under-strap tension stays at the cradle angle and is stated as about 1.9 x the real path tension (conservative). No meat_haul number changed, so `meat_haul_modes.md` stands.
- **Stale hinge 0.86 (orchestrator item 5):** `crown_gnl.md` and `bl047_frame_items.json` carry a superseded note (BL-049 hinge 1.30 inboard-up), kept by `crown_gnl.py` on a re-run.

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
| h1_assembled.stl | 995.1 | 996.6 | True / 1 | |
| h1_lower_flat.stl | 423.4 | 425.6 | True / 1 | [321.1, 299.6, 76.7] (rot 163.5, brim spare [2.95, 4.42]) |
| h1_upper_flat.stl | 543.5 | 543.5 | True / 1 | [309.4, 280.1, 64.4] (rot 90.0, brim spare [14.61, 23.88]) |
| test_pieces/us_route_stay_R.stl | 125.9 | 127.0 (as assembled 140.7) | True / 1 | [117.0, 120.0, 64.7] |

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
| us2 | r 9 circle (BL-049) | 1.48 (3.29) | 1.25 (2.78) | 0.82 (1.82) | 1.82 | 0.82 |
| us2 | real section (BL-051) | 1.49 (3.32) | 1.18 (2.62) | 1.13 (2.5) | 2.5 | 1.13 |

Cradle load families, worst over each family's fleet variants (real stay section; strength / fatigue / region):

| lug | 720 N at 31.3 deg (BL-049 envelope) | lane, 70 mm design belly | lane, 50 mm belly |
|---|---|---|---|
| us1 | 720.0 N: 1.91 / 0.86 (root) | 529.3 N: 2.42 / 1.09 (root) | 643.8 N: 2.11 / 0.95 (root) |
| us2 | 720.0 N: 2.93 / 1.32 (arm) | 638.8 N: 3.34 / 1.5 (root) | 860.2 N: 2.5 / 1.13 (root) |

Belly sweep (`belly_sweep`, us_route.cradle_span at the 53 kg float limit, factored 1.6 g x 1.5):

| belly mm | US1 N / leg deg / strength / fatigue | US2 N / leg deg / strength / fatigue |
|---:|---|---|
| 50 | 643.8 / 35.5 / 2.11 / 0.95 | 860.2 / 16.9 / 2.5 / 1.13 |
| 55 | 605.7 / 38.2 / 2.23 / 1.0 | 789.0 / 18.4 / 2.71 / 1.22 |
| 60 | 575.1 / 40.6 / 2.29 / 1.03 | 730.1 / 20.0 / 2.92 / 1.31 |
| 70 | 529.3 / 45.0 / 2.42 / 1.09 | 638.8 / 23.0 / 3.34 / 1.5 |

**Governing load:** the 50 mm belly row. The belly is set by how hard the hunter cams the straps; meat_haul specifies about 70 mm but nothing stops a harder cinch, and a flatter cradle raises the tension fast. The 720 N row at 31.3 deg (meat_haul's legacy angle from the stay x) is kept in the record but is not a load either lane sees: it overstates US1 (real max 644 N) and understates US2's tension (860 N), with the wrong direction for both.

US2 clevis joint (`h1_bedfit.joint_check`, recessed heads, all rows): share 0.6 strength 3.11, fatigue 1.4; share 1.0 1.87 / 0.84. Strap route (`us_route.py`, 'print_lanes', on the new STL): worst US1 12.4 / US2 14.6 mm, pass True.

Spreader z 142 notch (`spreader.us2_notch_check`): support line y 10.01 (z 127) to 11.84 (z 160); the print inside the notch footprint is the stay crown, 0.17 mm below that line at its closest. BL-050 measured 2.31 mm because the crown was cut away; the 1.5 mm 'root air' it passed was the defect. The arm root now blends into the stay under the crown and never reaches the sheet plane, and the crown is the sheet's support along the whole stay, so the rule is: nothing in the notch stands proud of the support line (proud -0.17 mm, pass True). The notch no longer clears anything (no cleat on the stay at z 142 since BL-049): closing it gives the sheet bearing there too (owner option, needs the spreader re-run).

### 3a. US2 clevis bolt heads

`h1_bedfit.ClevisJoint` (BL-051): counterbore 9 mm x 4 mm from the outer face (|x| 183), head bearing at |x| 179 with no washer, bolt axes at yc -2.8 (counterbore wall 2.5 mm to the block's wearer face, 2.0 mm to its z faces), M5 x 35, tail hole to |x| 143.5. Joint capacities: washer_bearing_n 2556.7, plug_shear_out_n 5414.4, bolt_tension_n 8896.3, bolt_fatigue_n 3177.2, hole_bearing_n 2301.1, bolt_shear_n 7193.9, contact_mpa 70.4 (bearing ring and shear-out now from the head, the weaker end). `us_route.head_clearance` on the same 12 fine drapes (15 / 19 / 23 in, fill / meat, R / L):

| torso | case | side | cloth to head mm | cloth to the clevis outer slab mm |
|---:|---|---|---:|---:|
| 15 | fill | R | 0.9 | -3.4 |
| 15 | fill | L | -1.7 | -3.8 |
| 15 | meat | R | 3.2 | -3.3 |
| 15 | meat | L | -1.2 | -4.0 |
| 19 | fill | R | 13.1 | -3.7 |
| 19 | fill | L | 3.4 | -3.9 |
| 19 | meat | R | 2.1 | -3.6 |
| 19 | meat | L | -1.3 | -3.7 |
| 23 | fill | R | 12.1 | -3.9 |
| 23 | fill | L | 11.3 | -3.7 |
| 23 | meat | R | 6.4 | -3.6 |
| 23 | meat | L | -1.4 | -4.0 |

Heads: worst -1.7 mm (BL-050: -1.1); clevis slab worst -4.0 mm; strap ribbon -2.8 mm (a centre-line lower bound; the real strap route on the STL is the print_lanes check above, which passes). The sim has no frame outboard of the stays, so negative numbers mean the free cloth hangs through frame parts there. With the heads sunk, the first thing the bag meets is the clevis's flat outer face (rounded edges r 1.5), about 4 mm inside the free drape on every case. Meeting >= 3 mm there would take the bag's side panel let out about 7 mm over z 127-157 near x 183 (pack-designer), or the lane / outer cheek moved in, which BL-050 ruled out (bed and strap clearance).

## 4. Body, and the US1 root (item 2)

`h1_buckling.full_check` on the restored body (`h1_lanes.body_solid`, lane loads, real crown; cache `check_m1_u2.5_im3_bl051_crown`) against the BL-049 / BL-050 body (`check_m1_u2.5_im3_bl049_lanes`; BL-050 changed only the print, not the voxel body):

| basis | strength | fatigue | creep | buckling | z 234 joint strength / fatigue |
|---|---|---|---|---|---|
| fine_sm8 | 1.678 -> **1.679** | 1.247 -> **1.258** | 2.660 -> 2.683 | 1.171 -> **1.171** | 2.08 / 1.71 |
| fine | 1.678 -> **1.679** | 1.263 -> **1.271** | 2.694 -> 2.712 | 1.138 -> **1.138** | 2.08 / 1.71 |
| beam | 1.611 -> **1.613** | 1.223 -> **1.235** | 2.610 -> 2.635 | 1.250 -> **1.256** | 1.96 / 1.25 |
| fine_sm8.cyc | 1.678 -> **1.679** | 0.829 -> **0.834** | 1.768 -> 1.778 | 1.106 -> **1.095** | 2.11 / 1.09 |
| cradle on the lane, 70 mm belly (new) | **2.661** | **1.197** | 2.554 | **1.904** | |
| cradle on the lane, 50 mm belly (new) | **2.377** | **1.070** | 2.282 | **1.313** | |
| bag-off cradle (lanes, 720 N at 31.3 deg) | 2.538 -> **2.563** | 1.142 -> **1.153** | 2.437 -> 2.460 | 5.138 -> **5.100** | |

Raster 888.9 -> 892.8 g. Governing fatigue region (fine_sm8): lumbar struts / pan / peak stay L lower sleeve z 160-240 (branch / strut root). The fatigue minimum of the cycled basis (fine_sm8.cyc, the BL-024 cinch-cycled set) has been below 1 since BL-024 (R1 hold for MT-1, h1_lanes.md section 3); the crown does not change it.

**Which US1 number governs.** Model: the stub model. The whole-body model applies each US pin load at the stay node (force + the lane moment, h1_lanes.lane_items): the arm carries no pin load there, so its root sees only the stay's global stress. The stub model routes the pin load through the cheeks and the arm into the root, which is what loads that root; its fixed stub ends leave out the lower branch (conservative) and the global stay stress (unconservative). The stub number is the one to design to until the T1 / MT-1 strain gauge at the US1 root settles it. Whole body 1.153 (720 N row; BL-049: 1.142). Load: on the 720 N / 31.3 deg envelope the stub reads 0.8 (circle) / 0.86 (real section), but US1 on its lane sees at most 643.8 N (50 mm belly) at a steeper leg: real section **1.09** at the 70 mm design belly, **0.95** at 50 mm, 1.00 at 55 mm. So the US1 root meets the fatigue requirement (>= 1.0 at the 1.6 g walking peak, 1e5 cycles) at the design belly and fails it by 5 % if the straps are cammed flatter than about 55 mm. Options: a minimum belly in the meat-haul instructions (60 mm: US1 1.03, a strap mark or a 60 mm gauge on the B-16 channel; owner), or the root fix of BL-049 proposal 2 (run the US1 arm onto the lower branch). Either way the first article's T1 and MT-1 carry a strain gauge at the US1 root.

**Kit text (for BL-050B; `physical_test_kit.py` is theirs and not edited here):** physical_test_kit.py, test T1 (and its TEST_PLAN / test_register rows): add 'strain gauges (1 mm foil, 120 ohm, quarter bridge, cyanoacrylate on the sanded PAHT) on the US1 arm root (R side, bag face, 3 mm off the stay surface, gauge axis along the arm) and on the US2 arm root (same place); record at 0 / 150 / 300 lb in T1 (a)/(b) and at 240 / 480 / 720 N per pin in the MT-1 cradle pull; PASS: measured root stress (strain x 3.86 GPa, youngs_modulus_xy_mpa of data/materials pa12_cf_fdm_paht) <= the h1_crown lug model's root stress at that load (ASSUMPTION US1-STUB-GOVERNS / STAY-STUB / CROWN-SECTION)'. The CLEVIS-SHARE pull's 'optional strain gauge at the US2 arm root' becomes required, same gauge place. US ROUTE step (0) and the CLEVIS-SHARE pull: the clevis now takes 2 Ti M5 x 35 DIN 7984 (HW-US2-SCR; was M5 x 40) with the heads in the printed counterbores, no washer under the head, and 2 x 10 mm OD DIN 433 washers on the nut side only (HW-US2-WSH; was 4); add 'check the heads sit below the clevis face'. MT-1 cradle pull: measure and record the belly (minimum-belly decision, ASSUMPTION BELLY-MIN).

## 5. Mass

| item | g | oz |
|---|---:|---:|
| print: stay crown restored (assembled BL-051 996.6 - BL-050 995.1) | +1.5 | +0.05 |
| attachment: BL-050's US1 / US2 pins + sleeves row retired (double count with the cradle rows) | -10.8 | -0.38 |

Ledger row BL051 (`huntkit/mass/ledger.py`, from this json); the BL050 step drops by the retired 10.8 g (`analysis/weight_rollup_v2.json`). Printed: lower 425.6 g, upper 543.5 g, clevises 27.5 g (996.6 g, 2.20 lb). Lug arms as unioned 69.84 g (the union adds a little less than before: the crown now holds part of their root).

| frame: US2 clevis hardware M5 x 35, 4 washers (was M5 x 40, 8 washers) | -3.20 | -0.113 |

**Mass reductions that keep the SF (not applied):** the restored crown holds no margin that governs anywhere else. The US2 lug has 1.13 at the 860 N row on the real section, just under the 1.15 scatter goal: no taper. The US1 arm cannot lose anything (0.95 at a 50 mm belly).

## 6. BOM mix-up (washers 10 / 12 mm, screws M5 x 35 / x 45)

Both joints use M5 Ti DIN 7984 screws and A2 washers that differ only in length / OD. The print README's shopping list now gives each its own BOM line and ID: **HW-J234-SCR** M5 x 45 (z 234 joint, 4), **HW-J234-WSH** 12 mm OD (z 234 joint, 8), **HW-US2-SCR** M5 x 35 (US2 clevis, 4; M5 x 40 until the BL-051 counterbore), **HW-US2-WSH** 10 mm OD DIN 433 (US2 clevis, 4, nut side only), **HW-M5-NUT** (both, 8), with a callout to bag and label them apart and the IDs in the assembly steps. Consequence of a swap: an M5 x 35 at z 234 does not reach through the nut; an M5 x 45 in the clevis bottoms in the blind tail hole (|x| 143.5) 10 mm before the head seats; a 10 mm washer at z 234 loses the washer-bearing area the joint is sized on; a 12 mm washer does not fit the clevis trap. The ledger's BL050 hardware row said 'M5 x 35' while BL-050 bought M5 x 40; it now prints the names from `h1_bedfit.json` (what BL-050 booked), and the BL051 row books the change to M5 x 35 with its grams.

## 7. Assumptions

- ASSUMPTION BELLY-MIN: The cradle belly stays >= 55 mm (US1 root fatigue 1.00; 60 mm proposed for the instructions, 1.03); a 50 mm belly is the governing check case (US2 860 N). Settled by: Owner decision on the instruction; MT-1 cradle pull with the belly measured, strain gauge at the US1 root.
- ASSUMPTION HEAD-BEAR: The US2 clevis screw heads bear on the counterbore floor in PAHT-CF with no washer (bearing ring from the 8.5 mm head, the weaker end in the joint check). Settled by: CLEVIS-SHARE pull on the CA-1 rig: no head pull-in or crack at the counterbore after 1e5 cycles.
- ASSUMPTION CLEVIS-FACE: The bag panel rests on the clevis's flat outer face (free drapes 3.3-4.0 mm inside it); contact on a flat, edge-rounded printed face is not a wear or load point. Settled by: FIT-US / T9 on P1: inspect the bag panel over the clevis for abrasion after the T9 walk.
- ASSUMPTION CROWN-BRIDGE: The stay section over each old stub site is the intersection of the plain stay sections 4-8 mm beyond each end of the strip zone (h1_lanes._crown_bridge); what the topology body had under the old stub is unknown (the stub was a keep-in). Settled by: Not needed for strength (the FEA uses this body); first-article slice / caliper of the crown at z 96 and z 142 against z 122 (within 0.5 mm).
- ASSUMPTION CROWN-SECTION: The lug FEA's stay stub takes the print's plain stay section next to each station (US1 z 116, US2 z 122) in place of the r 9 circle; the stub still ends at +/-22-23 mm and leaves out the lower branch. Settled by: Strain gauge at the US1 and US2 arm roots in T1 (and the MT-1 cradle pull) on the first article.
- ASSUMPTION NOTCH-PROUD: The z 142 spreader notch now sits over a plain stay crown: the rule is that nothing in the notch footprint stands proud of the sheet's support line (BL-050's 1.5 mm air rule was measured on the cut crown). Settled by: Spreader dry fit on the first article: the sheet edge each side of the notch bears on the crown, no rocking.
- ASSUMPTION US1-STUB-GOVERNS: For the US1 arm root the stub model governs over the whole body (see section 4). Settled by: Strain gauge at the US1 arm root, T1 (a) / (b) and the MT-1 cradle pull: measured root strain x E / the stub model's root stress at the same load <= 1.0.
- ASSUMPTION Carried: CLEVIS-SHARE, CLEVIS-DRY, CLEVIS-PRINT, SEAM-FLOOR, HEAD-PROUD, BED-ROT (h1_bedfit.md 7); STAY-STUB, LANE-MOMENT, HINGE-ROW, FI99-RULE (h1_lanes.md 6); US-FLEET, US-TOPO, DRAPE-US (us_route.json). Settled by: as there

## 8. Screenshots

- `outputs/screens/20261113_BL051_1.png`
- `outputs/screens/20261113_BL051_2.png`
- `outputs/screens/20261113_BL051_3.png`
- `outputs/screens/20261113_BL051_4.png`
