# Pack 5200 frame v2 - all HA-LS-1 load cases (19 in torso)

## Pack 5200 frame v2, 19 in torso (HA-LS-1)

Frame: height 0 mm (0.0 in), stays straight, torso setting 19 in -> yoke at z = 0 mm, haul mode = False.

| load case | load | min SF | req. | critical member | buckling factor | bond SF (avg / Volkersen peak) | hip share | pass |
|---|---|---|---|---|---|---|---|---|
| static_carry | 68 kg (150 lb) x 1 g | 3.98 | 2 | plv32 (lumbar_plate) | 10.2 | 111.30 / 33.30 mid_hub_R | 0.80 | yes |
| drop_2p5g | 68 kg (150 lb) x 2 g | 1.99 | 1.5 | plv32 (lumbar_plate) | 5.1 | 55.65 / 16.65 mid_hub_R | 0.80 | yes |
| side_hill_torsion | 68 kg (150 lb) x 1.6 g | 2.29 | 1.5 | plv32 (lumbar_plate) | 5.7 | 11.99 / 3.41 crown_corner_L | 0.80 | yes |
| single_stay_setdown | 68 kg (150 lb) x 2 g | 4.15 | 1.5 | SL330-MB0 (mid_bar) | inf | 6.40 / 1.91 mid_hub_L | - | yes |
| meat_shelf_heavy_low | 68 kg (150 lb) x 2 g | 1.90 | 1.5 | SR250-SR272.7 (stay_upper_R) | 3.8 | 43.56 / 9.77 upper_hub_R | 0.80 | yes |
| tall_load | 68 kg (150 lb) x 2 g | 1.82 | 1.5 | plv32 (lumbar_plate) | 3.9 | 44.37 / 9.90 upper_hub_R | 0.80 | yes |
| overload_haul | 91 kg (201 lb) x 1.6 g | 1.78 | 1 | SR250-SR272.7 (stay_upper_R) | 3.6 | 40.69 / 9.13 upper_hub_R | 0.80 | yes |
| hipbelt_off_abuse | 68 kg (150 lb) x 1.5 g | 1.36 | 1 | CLbot-CL530 (crown_leg_L) | 3.0 | 11.86 / 3.55 upper_hub_R | 0.00 | yes |
| tall_load_posts | 68 kg (150 lb) x 2 g | 1.97 | 1.5 | plv32 (lumbar_plate) | 4.6 | 43.64 / 9.78 upper_hub_L | 0.80 | yes |

Mass of load-path tubes (fittings, bonded nodes, shelf and hardware not included):

| member group | section | material | length mm | mass g (oz) |
|---|---|---|---|---|
| stay_lower_L | composite_tube(od=20, t=0.815, n_plies=5) | cfrp_t300_3k_woven_epoxy_ply | 130 | 9.8 (0.35) |
| stay_upper_L | composite_tube(od=20, t=0.815, n_plies=5) | cfrp_t300_3k_woven_epoxy_ply | 400 | 30.2 (1.07) |
| stay_lower_R | composite_tube(od=20, t=0.815, n_plies=5) | cfrp_t300_3k_woven_epoxy_ply | 130 | 9.8 (0.35) |
| stay_upper_R | composite_tube(od=20, t=0.815, n_plies=5) | cfrp_t300_3k_woven_epoxy_ply | 400 | 30.2 (1.07) |
| lumbar_plate | plate_strip_flanged(w=20, t=1.5, flange=25) | cfrp_plate_quasi_iso | 1902 | 0.0 (0.00) |
| lumbar_plate_shear | generic(A=46.4737, Iy=1, Iz=1, J=1) | plate_shear_equivalent | 2228 | 0.0 (0.00) |
| hip_pivot | tube_round(od=12, t=3) | ti_6al_4v | 98 | 25.0 (0.88) |
| mid_bar | composite_tube(od=18, t=0.94, n_plies=6) | cfrp_t300_3k_woven_epoxy_ply | 230 | 17.9 (0.63) |
| upper_bar | composite_tube(od=22, t=0.94, n_plies=6) | cfrp_t300_3k_woven_epoxy_ply | 230 | 22.1 (0.78) |
| crown_leg_L | composite_tube(od=16, t=1.19, n_plies=8) | cfrp_t300_3k_woven_epoxy_ply | 430 | 36.9 (1.30) |
| crown_leg_R | composite_tube(od=16, t=1.19, n_plies=8) | cfrp_t300_3k_woven_epoxy_ply | 430 | 36.9 (1.30) |
| crown_top_bar | composite_tube(od=18, t=0.94, n_plies=6) | cfrp_t300_3k_woven_epoxy_ply | 230 | 17.9 (0.63) |
| crown_spine | composite_tube(od=20, t=0.94, n_plies=6) | cfrp_t300_3k_woven_epoxy_ply | 300 | 26.0 (0.92) |
| **total tubes** | | | | **262.7 (9.27)** |

Fatigue screen (1.6 g carry, pulsating R = 0, required 1e+05 cycles):

- metal (Kt = 2, Goodman + Basquin): min life inf cycles at pivot_boss (Smax 24 MPa) -> ok
- CFRP: max FI at 1.6 g = 0.402 (limit 0.5) at plv32 -> ok
- bonds: max tau_avg 0.23 MPa vs 6.00 MPa (30% of lap shear) at mid_hub_R -> ok

![deformed](frame_sizing_cases_19in_deformed.png)

![utilisation](frame_sizing_cases_19in_utilization.png)

## Method and assumptions

- Solver: `huntkit.fea.frame` 3D Euler-Bernoulli frame, 6 DOF/node, members subdivided (2 elements
  per member segment); linear static; linear buckling from the consistent geometric stiffness.
  Verified against closed-form solutions in `tests/test_fea.py`.
- Metal SF = design yield / von Mises at the extreme fibre (peak axial+bending combined with peak
  torsion+transverse shear; conservative). Design yield = MMPDS S-basis when the material record
  has it (7075-T6: 462 MPa), else typical.
- CFRP SF = 1 / Tsai-Wu inverse strength ratio of the worst ply (24 points around the tube wall,
  membrane running loads at the mean radius, Ny = 0), strengths knocked down x0.8 hot/wet and a
  further x0.65 on compression (impact). Wall effective stiffness from CLT (membrane A-matrix).
- ASSUMPTION: body interface springs (global axes) - hipbelt kx 20 / ky 30 / kz 40 N/mm total,
  shoulder yoke 4 / 8 / 10 N/mm, load lifters at the stay tops 0 / 6 / 3 N/mm; the shoulder+lifter
  vertical stiffness is rescaled per case so the hipbelt carries 80 % of the vertical load.
- ASSUMPTION: bag load = equal nodal forces at the bag attachment points plus rigid-link moments for
  the CG offset aft; meat shelf = rigid shelf on the pivots with its tip strapped to mid-frame anchors;
  tall load = weight on the shelf pivots, overturning moment reacted by horizontal lashing at the
  upper lash points. Frame self-weight ignored (<0.5 % of load).
- ASSUMPTION: single-stay set-down = impact force (load x 2.5 g vertical + 0.2 friction) at one
  stay foot balanced by the load's d'Alembert inertia (inertia relief, free-free solve).
- Bonded joints: average bond shear vs lap-shear strength x0.8 hot/wet (SF governs), Volkersen
  elastic peak reported for information; bending treated as axial line load around the bond,
  transverse shear assumed to bear on the socket lip, peel not modelled.
- Fatigue: pulsating 0 -> 1.2 g static-carry stress; metal Goodman + Basquin with Kt = 2;
  CFRP FI limit 0.5; bonds 30 % of lap shear. Screening level only.
- Not covered: local tube crushing at clamps/fittings, fitting/node stress, bearing at shelf pivots,
  large-displacement effects, HDPE framesheet / hipbelt plate (use `huntkit.fea.plate`).
