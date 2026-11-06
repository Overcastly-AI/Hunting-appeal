# HA-LS-1 rev C production verification

Owner: structural-fea-engineer, 2026-11-06. Standard: **HA-LS-1 rev C** ([load_standard.md](load_standard.md) §4.2, owner decision 2026-11-06 in `docs/DECISIONS.md`). Code: `huntkit/gendesign/rev_c_verification.py` (engine: `frame_cg_recheck.py`). Results: [rev_c_verification_results.json](rev_c_verification_results.json). Tests: `tests/test_load_standard_rev_c.py`, `tests/test_rev_c_verification.py`.

```
python -m huntkit.gendesign.rev_c_verification      # about 25 min on 4 cores
```

Rev C inputs: bag cases (C1–C4, C8) **205 mm** aft at CG z **550**; meat cases (C5, C7) **190 mm**; tall cases (C6, C6p) **185 mm**; bag couple on the crown top bar **and** on the IM3 hooks (worse governs); crown hood 52.5 N/g + 2 guys 34.6 N/g each in C5 / C7; ties on the bar ≥ 25 mm webbing. Parts as released: socket-free PAHT-CF branch body, carbon crown **with the rev C fix** (frame.yaml), Sandwich v2 spreader with the **7 mm** core (BP-06 rev C).

## Summary: every load-path part, rev C, worst torso

Margin = SF / requirement; pass ≥ 1.00. Each row is the worse of the crown-bar and the IM3 couple variant unless the check says which.

| part | check | margin | governing set / location | basis | pass |
|---|---|---:|---|---|---|
| printed body | strength, couple on crown bar | **1.51** | hipbelt_off_abuse|15, upper bar / pawl housing | 1/FI99, factored | yes |
| printed body | fatigue, couple on crown bar | **1.14** | C:static_carry|15 | C1 at 1.6 g, PAHT 0.3 | yes |
| printed body | creep-rupture, couple on crown bar | **2.44** | C:static_carry|15 | C1 at 1 g, 40 C 8 h, 0.4 | yes |
| printed body | strength, couple on IM3 hooks | **1.54** | hipbelt_off_abuse|15, upper bar / pawl housing | 1/FI99, factored | yes |
| printed body | fatigue, couple on IM3 hooks | **1.04** | C_im3:static_carry|15 | C1 at 1.6 g, PAHT 0.3 | yes |
| printed body | creep-rupture, couple on IM3 hooks | **2.23** | C_im3:static_carry|15 | C1 at 1 g, 40 C 8 h, 0.4 | yes |
| carbon crown (fixed) | spine FPF, crown bar | **1.18** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | legs FPF, crown bar | **1.39** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | top bar FPF, crown bar | **1.38** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | corner bond average, crown bar | **2.34** | tall_load_posts|15 | beam model, knocked down | yes |
| carbon crown (fixed) | corner bond Volkersen peak, crown bar | **1.22** | tall_load_posts|15 | beam model, knocked down | yes |
| carbon crown (fixed) | leg ring crush, crown bar | **2.78** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | bushing bearing, crown bar | **20.94** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | member fatigue (FI <= 0.5 at 1.6 g), crown bar | **3.27** | static_carry|15 | beam model, knocked down | yes |
| carbon crown (fixed) | buckling (>= 1.5 x factor), crown bar | **1.85** | hipbelt_off_abuse|23 | beam model, knocked down | yes |
| carbon crown (fixed) | corner-bond fatigue, average, crown bar | **9.78** | static_carry|15 | tau(1.6 g) <= 0.3 x lap shear | yes |
| carbon crown (fixed) | corner-bond fatigue, Volkersen peak, crown bar | **3.39** | static_carry|15 | peak tau(1.6 g) <= 0.3 x lap shear | yes |
| carbon crown (fixed) | spine FPF, IM3 | **1.18** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | legs FPF, IM3 | **1.12** | hipbelt_off_abuse|23 | beam model, knocked down | yes |
| carbon crown (fixed) | top bar FPF, IM3 | **1.25** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | corner bond average, IM3 | **4.33** | side_hill_torsion|15 | beam model, knocked down | yes |
| carbon crown (fixed) | corner bond Volkersen peak, IM3 | **1.76** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | leg ring crush, IM3 | **2.33** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | bushing bearing, IM3 | **17.60** | hipbelt_off_abuse|15 | beam model, knocked down | yes |
| carbon crown (fixed) | member fatigue (FI <= 0.5 at 1.6 g), IM3 | **1.36** | static_carry|23 | beam model, knocked down | yes |
| carbon crown (fixed) | corner-bond fatigue, average, IM3 | **6.09** | static_carry|23 | tau(1.6 g) <= 0.3 x lap shear | yes |
| carbon crown (fixed) | corner-bond fatigue, Volkersen peak, IM3 | **2.11** | static_carry|23 | peak tau(1.6 g) <= 0.3 x lap shear | yes |
| torso adjust | rack (C) | **6.27** | hipbelt_off_abuse|19 | 5328 N / factored axial | yes |
| torso adjust | pawl cheek, 304 bushing (C) | **1.40** | hipbelt_off_abuse|15 | 1/FI99 | yes |
| torso adjust | cam hold, walking (C) | **66.99** | static carry x 1.6 | 700 N slip | yes |
| torso adjust | rack (C_im3) | **6.27** | hipbelt_off_abuse|19 | 5328 N / factored axial | yes |
| torso adjust | pawl cheek, 304 bushing (C_im3) | **1.41** | hipbelt_off_abuse|15 | 1/FI99 | yes |
| torso adjust | cam hold, walking (C_im3) | **68.63** | static carry x 1.6 | 700 N slip | yes |
| printed body | segment joint dowel pull-out (z 234) | **2.25** | C_im3:drop_2p5g|23 | MMA 6 MPa hot/wet | yes |
| attachments | fairlead hinge cheek strength | **2.97** | tall_load | 1/FI99, 1 mm mesh | yes |
| attachments | fairlead hinge cheek fatigue | **1.67** | tall_load | 1.6 g, PAHT 0.3 | yes |
| attachments | fairlead im3 cheek strength | **3.60** | meat_straps | 1/FI99, 1 mm mesh | yes |
| attachments | fairlead im3 cheek fatigue | **2.02** | meat_straps | 1.6 g, PAHT 0.3 | yes |
| attachments | hinge pin 7075 shear yield | **14.46** | tall_load | factored | yes |
| attachments | hinge UHMWPE sleeve bearing | **2.32** | tall_load | factored | yes |
| attachments | bag hooks (2200 N rated) | **4.30** | side_hill_torsion@IM3 | rated / factored | yes |
| attachments | meat-strap hooks (1500 N) | **2.48** | meat_straps | rated / factored | yes |
| attachments | hinge-eye bartack | **3.73** | tall_load | 2700 N / factored | yes |
| attachments | crown bar wall under the hood | **9.89** | C5 158 N factored | ring, FPF | yes |
| attachments | crown bar wall under a guy (30 mm) | **3.16** | C5 112 N factored | ring, FPF | yes |
| attachments | crown bar wall, 210 N tie on 25 mm webbing | **1.40** | generic tie | >= 25 mm rule | yes |
| spreader 7 mm core | first-ply failure | **1.25** | US2 corner relief | factored meat + bone | yes |
| spreader 7 mm core | fatigue (FI <= 0.5 at 1.6 g) | **1.09** | US2 corner relief | walking | yes |
| spreader 7 mm core | sandwich local (core shear, wrinkling, crush) | **1.11** | bone patch | factored | yes |
| spreader 7 mm core | no bottoming: walking air / 3 mm mesh | **4.16** | walking | air >= 3 mm | yes |
| spreader 7 mm core | skin pressure over the rails (comfort, <= 14 kPa) | **1.01** | 13.83 kPa, x 96, z 412 | rail r120_b80, Golriz 2017 | yes |

**Every HA-LS-1 rev C check passes** on the released parts.

Comfort (not HA-LS-1): walking **skin pressure over the back rails 13.83 kPa** at the 190 mm meat CG, against the 14 kPa limit (Golriz 2017), with the released rails (`spreader.RAIL_DESIGN` = `back_rail.released()`, r120_b80: 120 mm L200 rails on 80 mm 1 mm-twill backers, pack-designer D-32). It agrees with the pack-designer's 13.77 kPa (named positions, 2 mm); the 24 mm bone grid finds the worst at x 96, z 412. With the old 100 mm rails it was 15.5 kPa. Margin to the limit is small (1 %).

## 1. Printed body (2 mm voxels, FI99), min margin per case

| case | factor | couple on crown bar | couple on IM3 | location (crown bar) |
|---|---:|---:|---:|---|
| C1 static_carry | 2 | 3.05 (15) | 2.78 (15) | stay L below the sleeve |
| C2 drop_2p5g | 1.5 | 2.03 (15) | 1.86 (15) | stay L below the sleeve |
| C3 side_hill_torsion | 1.5 | 2.31 (15) | 2.16 (15) | stay R below the sleeve |
| C4 single_stay_setdown | 1.5 | 3.42 (23) | 3.37 (23) | stay L below the sleeve |
| C5 meat_straps | 1.5 | 2.39 (23) | – | stay R below the sleeve |
| C6 tall_load | 1.5 | 2.94 (15) | – | stay L below the sleeve |
| C6p tall_load_posts | 1.5 | 2.85 (15) | – | stay L below the sleeve |
| C7 overload_haul | 1 | 3.36 (23) | – | stay R below the sleeve |
| C8 hipbelt_off_abuse | 1 | 1.51 (15) | 1.54 (15) | upper bar / pawl housing |
| fatigue (C1 at 1.6 g) | | 1.14 | 1.04 | |
| creep-rupture (C1 at 1 g, 40 °C) | | 2.44 | 2.23 | |
| info: fatigue with the meat at 1.6 g | | 1.34 | | |

Printed body mass on the 2 mm raster: **823 g**.
Segment joint at z 234 (2 × 5 mm dowels per flange, 35 mm embed): worst pull-out SF 2.25 (C_im3:drop_2p5g|23).

## 2. Carbon crown with the rev C fix (beam model)

| check | fixed, crown bar | fixed, IM3 | as built, crown bar | as built, IM3 |
|---|---:|---:|---:|---:|
| spine FPF | 1.18 (hipbelt_off_abuse|15) | 1.18 (hipbelt_off_abuse|15) | 0.96 (hipbelt_off_abuse|15) | 0.96 (hipbelt_off_abuse|15) |
| legs FPF | 1.39 (hipbelt_off_abuse|15) | 1.12 (hipbelt_off_abuse|23) | 1.07 (hipbelt_off_abuse|15) | 0.86 (hipbelt_off_abuse|23) |
| top bar FPF | 1.38 (hipbelt_off_abuse|15) | 1.25 (hipbelt_off_abuse|15) | 1.13 (hipbelt_off_abuse|15) | 1.02 (hipbelt_off_abuse|15) |
| corner bond average | 2.34 (tall_load_posts|15) | 4.33 (side_hill_torsion|15) | 2.41 (tall_load_posts|15) | 4.30 (side_hill_torsion|15) |
| corner bond Volkersen peak | 1.22 (tall_load_posts|15) | 1.76 (hipbelt_off_abuse|15) | 1.03 (tall_load_posts|15) | 1.48 (hipbelt_off_abuse|15) |
| leg ring crush | 2.78 (hipbelt_off_abuse|15) | 2.33 (hipbelt_off_abuse|15) | 1.99 (hipbelt_off_abuse|15) | 1.67 (hipbelt_off_abuse|15) |
| UHMWPE bushing bearing | 20.94 (hipbelt_off_abuse|15) | 17.60 (hipbelt_off_abuse|15) | 20.82 (hipbelt_off_abuse|15) | 17.52 (hipbelt_off_abuse|15) |
| member fatigue | 3.27 (static_carry|15) | 1.36 (static_carry|23) | 2.68 (static_carry|15) | 1.05 (static_carry|23) |
| buckling | 1.85 (hipbelt_off_abuse|23) | – | – | – |

### 2.1 Corner-bond fatigue (new)

HA-LS-1 fatigue rule for bonds: shear at 0 → 1.6 g × 68 kg ≤ 0.3 × lap shear (MMA on CFRP, × 0.8 hot/wet). From the C1 load path (1 g), SF_fat = 0.3 × SF(1 g) / 1.6. The rule names the shear, not which one; both are reported. The elastic Volkersen peak is the conservative reading (no yield redistribution in high-cycle fatigue).

| crown | variant | average: SF (set) | Volkersen peak: SF (set) | info: meat at 1.6 g, peak |
|---|---|---:|---:|---:|
| fixed (0.8 mm) | crown bar | 9.78 (static_carry|15) | 3.39 (static_carry|15) | 2.13 |
| fixed (0.8 mm) | IM3 | 6.09 (static_carry|23) | 2.11 (static_carry|23) | – |
| as built (0.5 mm) | crown bar | 10.16 (static_carry|15) | 2.89 (static_carry|15) | 1.57 |
| as built (0.5 mm) | IM3 | 5.42 (static_carry|23) | 1.54 (static_carry|23) | – |

## 3. Torso adjust

| | crown bar | IM3 |
|---|---:|---:|
| rack SF (5328 N) | 6.27 (hipbelt_off_abuse|19) | 6.27 (hipbelt_off_abuse|19) |
| factored pawl force y / z, N | 2156 / 850 | 2142 / 850 |
| pawl cheek (304 bushing) 1 / FI99 | 1.40 | 1.41 |
| static-carry crown axial, N (1 g) | 32 | 32 |
| tail pull to shorten while worn, N | 17 | 16 |
| cam hold SF walking / hipbelt off | 67 / 6.1 | 69 / 6.1 |
| tail pull to hoist, hipbelt off, N | 293 | 293 |

The hipbelt-off hoist pull stays above the ASSUMPTION 200 N one-hand limit: keep the instruction not to adjust the torso with the hipbelt off.

## 4. Attachments

Governing factored force per fairlead (both couple variants; `@IM3` = the IM3 couple variant), against the rev B record (`bag_attachment_results.json`):

| fairlead | rev B N (case) | rev C N (case) |
|---|---:|---:|
| hinge | 726 (tall_load) | 724 (tall_load) |
| im1 | 267 (meat_straps) | 273 (meat_straps) |
| im2 | 403 (tall_load_posts) | 512 (side_hill_torsion) |
| im3 | 554 (tall_load_posts) | 605 (meat_straps) |

| part | load N | SF | rule |
|---|---:|---:|---|
| fairlead hinge, printed cheek (1 mm voxels) | 724 | 2.97 (fatigue 1.67, creep 3.57) | 1 / FI99 ≥ 1 |
| fairlead im3, printed cheek (1 mm voxels) | 605 | 3.60 (fatigue 2.02, creep 4.31) | 1 / FI99 ≥ 1 |
| hinge pin 5 mm 7075, double shear | 724 | 14.5 | yield |
| hinge UHMWPE sleeve bearing | 724 | 2.32 | yield |
| bag hooks, rated 2200 N (side_hill_torsion@IM3, SR330) | 512 | 4.30 | rated ≥ factored |
| meat-strap hooks 1500 N (meat_straps, SR520) | 605 | 2.48 | rated ≥ factored |
| hinge-eye bartack 2700 N | 724 | 3.73 | |
| crown bar wall under the hood lip (158 N over 132 mm, 1.19 N/mm) | 158 | 9.89 | ring FPF |
| crown bar wall under a guy through the hood ear (30 mm) | 112 | 3.16 | ring FPF |
| generic tie 210 N on 20 mm webbing | 210 | 1.12 | **not allowed** (< 25 mm) |
| generic tie 210 N on 25 mm webbing | 210 | 1.40 | allowed |
| generic tie 210 N on 38 mm webbing | 210 | 2.14 | allowed |
| lifters: webbing / ladder lock / ladder hipbelt-off | | 188.1 / 4.2 / 1.7 | |

- The bag hooks are checked on the bag cases (C1–C3, C8) at the IM2 / IM3 eyes, including the IM3 couple variant; the meat-strap hooks on the meat and tall cases. The cloth-sim hood-off hook load (T0 472 N × 3.0 = 1415 N, bag_attachment.md §3) does not depend on the standard and stays SF 1.55.
- ASSUMPTION: the fairlead loads come from the beam model's default frame (`bag_attach._frame_model`), the same basis as the rev B attachment record.

## 5. Spreader, Sandwich v2 with the 7 mm core (BP-06 rev C)

Meat CG 190 mm (`spreader.MEAT_CG_MM`, from the load standard). Release procedure: 4 mm grid with a 24 mm bone grid, then 2 mm at the named positions; the worse governs.

| check | 7 mm core (production) | 6 mm core at rev C (2 mm, named) | rule |
|---|---:|---:|---|
| first-ply SF | 1.25 (US2 corner relief) | 1.13 | ≥ 1.0 factored |
| fatigue SF | 1.09 | 0.98 | FI ≤ 0.5 at 1.6 g |
| sandwich local SF | 1.11 | 0.99 | ≥ 1.0 |
| air walking / factored, mm | 12.5 / 6.1 | 12.7 / 6.6 | ≥ 3 / ≥ 0 |
| info: factored lean-torso air, gutter-bulge skin model, mm | 2.6 | 3.0 | sensitivity |
| factored lean-torso air with the lumbar-pan skin reference, mm | **11.9** | – | ≥ 0 (spreader_layout.md re-check method) |
| skin pressure, kPa (comfort, not HA-LS-1; released 120 mm rails) | 13.83 | 13.77 | ≤ 14 |
| mass installed, g | 162.3 | 153.5 | |

Sheet 7.44 mm (7 mm core + 2 × 0.22 mm skins). Clip slot depth +1.0 mm (`spreader_v2_clip.dxf`, regenerated for the 7.44 mm sheet), clip SF 71.7. Files: `designs/pack_5200/cut/spreader/spreader_v2_cut.dxf`, `designs/pack_5200/cut/spreader/spreader_v2_clip.dxf`, `designs/pack_5200/cut/spreader/spreader_v2_drawing.pdf`. Cost about $207.

`spreader._SKIN_CACHE` bug fixed: the key now includes the meat force, so a changed meat load is never served a stale skin pressure (regression test `test_spreader_skin_cache_keys_on_meat_load`).

## 6. Masses of the load-path members

| member | g | basis |
|---|---:|---|
| printed branch body (2 mm raster, socket-free) | 823 | `solid_mass_g` here |
| crown crown_leg | 73.8 → **88.1** | beam model hardware mass, frame.yaml |
| crown crown_top_bar | 17.9 → **20.2** | beam model hardware mass, frame.yaml |
| crown crown_spine | 26.0 → **29.4** | beam model hardware mass, frame.yaml |
| adhesive (incl. lumbar-plate bond) | 29.1 → **32.4** | beam model hardware mass, frame.yaml |
| crown fix, booked | **+22.0** | spine 3.3 + legs 14.3 + bar 2.1 + bondline 2.2 (`frame_cg_recheck.fix_mass_total`) |
| Sandwich v2 spreader, installed, 7 mm core | 162.3 | 153.5 with the 6 mm core |

- No mass cut is recommended now. The governing margins are the body under the IM3 couple (fatigue) and the spreader's notch-root FPF; thinning either loses the pass.
- Possible later cut: if test T9 measures a bag CG ≤ 190 mm, re-run this check at the measured CG before dropping one leg ply (about −7 g).

## 7. Assumptions

- ASSUMPTION: the beam model supplies the load path into the printed body and the crown forces, as in every production check (frame_cg_recheck.md §8).
- ASSUMPTION: the IM3 couple variant puts the whole bag couple top on the IM3 anchors; reality lies between the two variants, and rev C takes the worse.
- ASSUMPTION: hood and guy loads are added on top of the full meat load in the beam model (conservative for the crown, slightly favourable for the stays: the aft pull offsets the meat push).
- ASSUMPTION: guy aft run 305 mm at every torso (314 mm free length at 19 in), as in frame_cg_recheck.md §5.1.
- ASSUMPTION: the hood lip is centred on the bar (x ±66); it floats ±9 mm between the legs, which moves a symmetric line load by less than a node spacing.
- ASSUMPTION: the beam model's crown top bar carries the +1 ply; the printed mid bar line is unchanged (frame.yaml `top_bar_section`). The 0.8 mm bondline applies to the two crown corners only (`crown_joint`). The fix study of 2026-11-05 applied both to the mid bar / every joint as well.
- ASSUMPTION: corner-bond fatigue uses the hot/wet lap shear (× 0.8) as the static reference.
- ASSUMPTION: the spreader face load is linear in the meat CG (frame_smooth.meat_normal_n); bone 20 % of 68 kg, part of the meat.

## Screenshots

- `outputs/screens/20261106_revc_1.png`
- `outputs/screens/20261106_revc_2.png`
