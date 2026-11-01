# Bag to frame: branch fairleads

The Spine bag hangs on the printed branching frame. The fairlead is a small cleat
grown on the bag face of each stay. A 5 mm 7075 pin through a UHMWPE sleeve holds a
short webbing eye. The bag clips to that eye. The branch window is not filled, and
nothing sits on the wearer side of the stay.

Code: `huntkit/gendesign/bag_attach.py`. Load standard: HA-LS-1 rev B.

## Recommendation

**Branch fairlead.** Eight identical printed cleats, at the hinge and at IM1–IM3, both sides.

- Added mass **113 g**. Pack goes from 2865 g to **2979 g (6.57 lb)**.
- Printed fairlead, fine mesh 1.00 mm. Minimum strength SF **2.97**. Minimum fatigue SF **1.67**.
- Pin double-shear SF **14.4** (7075-T6 S-basis). Sleeve bearing SF **2.32**.
- Bag off in about **34 s** (four hooks and two hinge pins). Back on in about **70 s**.
- Marginal hardware and filament about **$48**. Extra print time about **1.75 h**.

Bag-off is a required mode (owner, 2026-11-01). The same fairleads take the
meat straps eye-to-eye once the bag is off. Both haul modes, the wedge between bag and frame,
and the safety factors are in `analysis/meat_haul_modes.md`. The eight B-01 swells are accepted.

## Why this one

- A sleeve over the limbs is light and strong and hides the branch. The frame is the product.
- Webbing passed through the branch window has to come back on the wearer side of the stay.
  That strand lands in the pad gap. The window is kept open so the split stays visible.
- A magnetic buckle is rated 300 N. The hinge sees 726 N factored.
- A 25 mm side-release is rated 450 N. A 38 mm side-release is rated 900 N, SF 1.24 on the hinge, and that rating is an estimate. Neither is the closer.
- A cam will hold a pull and then walk under a day of gait. The torso-adjust study already rejected it as a lock.
- A rail covers the stay face, adds a slider that can tap, and weighs more than the fairleads.
- A printed clip's hook tongue is still at fatigue SF 0.28 with an
  18 mm root. The tongue is pulled across the layers, and a thicker
  root does not fix it. A cracked tongue means reprinting the frame. The fairlead's pin and eye come off.

The closer on IM2 and IM3 is the aluminium sliding-gate hook already assumed for the meat
harness (1500 N, 9 g). It sees the full station load. SF at the heavier clip is **2.71**. The hinge does not use a hook:
the bag's sewn eye is on the pin, so the bag can swing open for a bay load without leaving the frame.
The bartack on that eye is the v3.1 assumption, 2700 N, SF **3.72**.

## Loads

Factored force on one side. The vector is the beam-model node force times the case factor.
CG for the bag cases is 148 mm, the v3.1 bag. Set-down loads the foot, not these nodes.

| station | z mm | case | N | aft N | down N | what clips |
|---|---:|---|---:|---:|---:|---|
| hinge | 60 | tall_load | 726 | 190 | 700 | bag hinge and the bay pivot |
| im1 | 190 | meat_straps | 267 | 248 | 100 | meat strap IM1 only |
| im2 | 330 | tall_load_posts | 403 | 391 | 100 | bag clip and meat strap IM2, beside the branch window |
| im3 | 520 | tall_load_posts | 554 | 545 | 100 | bag clip and meat strap IM3 |

## Safety factors

Failure index is the layered PAHT check (in-plane, layer-normal, interlayer shear).
The 99th percentile is taken on the fairlead plastic, not on the clamped end of the stay stub.
Fatigue scales that index from the factored case down to the 1.6 g walking peak, then divides
into the 0.3 fatigue ratio. Creep rupture uses the 1 g stress and the 0.4 ratio.
Bearing allowable is 0.8 × Z tensile, because an aft pull bears across the layers.

| fairlead | host r mm | mesh mm | strength SF | fatigue SF | creep SF | bearing SF | added g |
|---|---:|---:|---:|---:|---:|---:|---:|
| hinge 1.00 mm | 9.4 | 1.00 | 2.97 | 1.67 | 3.56 | 5.97 | 6.2 |
| im3 1.00 mm | 16.8 | 1.00 | 3.91 | 2.20 | 4.70 | 7.82 | 6.1 |

Pin, double shear, governing hinge load: yield SF **14.4**, fatigue SF **16.1**. UHMWPE sleeve projected bearing SF **2.32** (9.1 MPa). The sleeve is a wear part. Replace it when the hole goes oval.

The coarse mesh is in the results JSON. The fine mesh is the number above. The cheek is 8 mm,
so a 1 mm element is eight through the thickness, not a one-voxel skin.

### Load lifters and the hipbelt

Neither interface moves onto the printed fairleads.

- **Hipbelt.** The Ti pivot is unchanged. Factored drop load at the 80 % hip share is **1600 N**. The mount's checked SF/required is 8.6 (static) and fatigue 19.7 (`analysis/generative_design.md`). The lumbar struts already carry it; the branch-frame minimum is 1.66 on hipbelt-off, which is this path with the belt undone.
- **Load lifters.** They stay on the carbon crown corner wraps, never on the extension posts (US 10,952,523). Spring split kz 3 / (3+10) of the non-hip load, angle 40.6° from horizontal. Factored tension **71 N** per side. Webbing SF **188** on the 25 mm polyester record. Ladder-lock slip SF **4.2** on that split, **1.69** with the hipbelt off, and **1.95** if the lifters are assumed to take half the non-hip load.
- The half-share sensitivity is the reason for a **tri-glide keeper** behind each ladder lock.
  The ladder lock adjusts. The keeper stops the tail so a slip cannot dump the lifter.
  The sewn loop on the crown lug is the structural end. It does not depend on the ladder lock.

## Options

| option | added g | detach s | governing SF | pass | why it lost, or why it won |
|---|---:|---:|---:|---|---|
| Branch fairlead | 113 | 34 | 1.67 | yes | shows the branch |
| Printed clip ear | 58 | 20 | 0.28 | no | tongue fatigue 0.28 at a 18 mm root |
| Webbing through window | 40 | 45 | 0.40 | no | return strand crosses the back |
| Sleeve over the limbs | 18 | 180 | 2.00 | no | hides the frame |
| Magnetic buckle | 90 | 12 | 0.41 | no | 300 N vs 726 N |
| Cam strap | 132 | 30 | 1.99 | no | creeps under gait |
| Rail and slider | 273 | 25 | 2.50 | no | covers the stay face |
| 25 mm buckle in series | 54 | 30 | 0.62 | no | 450 N break |
| 38 mm buckle in series | 108 | 30 | 1.24 | no | estimate, thin at the hinge |

Detach times are assumptions for gloved hands: 4 s a hook, 4 s a tethered pin, 10 s to clear the bag.
A sleeve is three minutes because the crown and the hipbelt block sliding it off.

## Mass and cost

| part | g |
|---|---:|
| printed fairleads (8) | 49.4 |
| 7075 pins (8) | 19.3 |
| UHMWPE sleeves (8) | 2.3 |
| bag hooks, 38 mm Al (4) | 36.0 |
| TPU hook sleeves (4) | 4.0 |
| webbing eyes, net of old stubs | -6.7 |
| bag-side straps | 17.9 |
| B-01 swell patches | 12.3 |
| elastic keepers | 3.6 |
| lifter tri-glide keepers | 6.0 |
| old LINK hardware removed | -30.8 |
| **delta** | **113** |

Pack **2979 g (6.57 lb)**. The 5.0 lb target is still missed, by **711 g**. This attachment is not the reason; the branch frame already was.

Cost is marginal. Filament $4.26, scrap $0.64, extra machine time $1.75, hooks pins and webbing $41.20. **$48** on top of the frame.

## How it is built

- Fairlead root is blended into the stay. It does not break into the 18 mm sleeve bore.
  The bore is cut after the fairlead in `frame_sdf`.
- Pin axis is lateral, so the hole lies in the print layers (build direction is frame y).
  The hole is a drawn loop in each layer, not a bridge in mid-air.
- UHMWPE sleeve, OD 7.2 mm, pressed into the cheeks. The pin turns in the sleeve, not in the nylon.
- Hinge pins (z 60) have a pull ring and a silicone washer, tethered to the bag eye.
  Leave them in and the bag hinges for a bay load. Pull them and the bag leaves.
- IM1 (z 190) keeps a captive eye for the meat strap. The bag does not clip there.
  IM2 (z 330) and IM3 (z 520) take a bag hook and a meat hook on the same eye.
- B-01 is only 20 mm aft of the stay centre, so the stay crown leaves a few millimetres.
  Each fairlead stands about 14 mm proud of the surface.
  A feathered 16 mm swell in B-01, 90 mm long, puts 2 mm of air over the cleat
  so it does not rub the cloth or print a point into the meat. The swell is inside the bag.
- Spreader sheet is notched 22 mm in height at each fairlead. The notch is at the edge landing,
  not in the window span. The rails and the mesh are untouched.
- Slack hooks sit under a 3 mm elastic keeper so an empty pack does not click on the stalk.
- Field repair: spare pin, spare sleeve, spare hook, in the hipbelt pocket. A cracked cleat
  is bypassed with a girth hitch of the same 38 mm webbing around the stay. The stay is intact.

## Screenshots

- `/workspace/docs/screens/20261101_attach_1_options.png`
- `/workspace/docs/screens/20261101_attach_2_closeup.png`
- `/workspace/docs/screens/20261101_attach_3_exploded.png`
- `/workspace/docs/screens/20261101_attach_4_fea.png`

## Assumptions

- Hook 1500 N and 9 g, bartack 2700 N, cam 1100 N / 22 g: carried over from DESIGN.md §4.5. Proof-test five hooks to 830 N and five bartacks to 1100 N.
- Pin price $2.50 and tri-glide 3 g are small-shop assumptions. Aluminium strength is the 7075 record, S-basis.
- UHMWPE sleeve strength is the sheet yield, 21 MPa. No fatigue number is published here; the sleeve is replaceable.
- B-01 patch 200 gsm is an assumption. The cloth is the same `challenge_ultra_200` as the panel; the gram is the patch area.
- Detach and attach seconds are gloved-hand assumptions, not a timed trial.
- Lifter share uses the spring stiffnesses in `load_cases.py`. The half-share line is a sensitivity, not the design case.
- Hip share 80 % is the load-standard assumption.
- Fairlead FEA is a stay stub with fixed ends. It does not re-solve the whole frame. The fairlead is added material, and the bore is not opened, so the published branch-frame factors still stand.
- Cam creep is the note already in `geometry.yaml` crown_retention (cam teeth hold, webbing walks).
- Rail mass uses `alu_6061_t6` density and a 20 × 4 mm bar, 520 mm, two of them, plus 12 g sliders (assumption).
- Sleeve mass is two 500 × 90 mm wraps at 200 gsm (assumption). It is rejected on the look, not on the grams.

## Open questions for the owner

1. The hook rating is still an assumption. If a bought hook breaks under 900 N, IM3 needs two hooks or a larger one. Proof-test five hooks to 830 N before the first sewn bag.
2. IM1 is a meat anchor only for now. A bag clip there adds two hooks. Leave it meat-only?
