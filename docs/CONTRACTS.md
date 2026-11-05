# Interface contracts

These are the shared data shapes between modules. Each module owner implements its side.
Consumers depend only on what's written here.

## 1. Material records — `data/materials/<category>/<id>.yaml`
Categories: `textiles`, `laminates_membranes`, `insulation`, `foams`, `composites`, `metals`,
`polymers`, `hardware`, `thread`, `webbing`.

```yaml
id: alu_7075_t6                # unique, snake_case, equals the filename stem
name: "Aluminum 7075-T6"
category: metals
generic: true                  # true = generic engineering grade; false = specific trade product
trade_names: []                # e.g. ["Dyneema Composite Fabric CT9HK.18"]; facts only
supplier_examples: []          # where the human can actually buy it
properties:                    # SI units in the key suffix, always
  density_kg_m3: 2810
  youngs_modulus_mpa: 71700
  shear_modulus_mpa: 26900
  poisson: 0.33
  yield_strength_mpa: 503
  ultimate_strength_mpa: 572
  fatigue_limit_mpa: 159        # with the basis noted in notes
  # textiles use: areal_density_gsm, denier, weave, tensile_warp_n_50mm, tensile_weft_n_50mm,
  #   tear_warp_n, tear_weft_n, abrasion_cycles_martindale, hydrostatic_head_mm,
  #   mvtr_g_m2_24h, ret_m2pa_w, stretch_pct, dwr, flammability, uv_rating
  # foams: density_kg_m3, compression_25pct_kpa, compression_set_pct, closed_cell (bool)
  # composites: E1_mpa, E2_mpa, G12_mpa, nu12, Xt_mpa, Xc_mpa, Yt_mpa, Yc_mpa, S_mpa, ply_thickness_mm
  # hardware/webbing/thread: breaking_strength_n, mass_g (per unit or per m), width_mm, tex
confidence: datasheet | handbook | estimate     # how much to trust the numbers
sources: ["MMPDS-01 Table 3.7.6.0(b1)", "https://..."]
cost_usd: {value: 0.0, per: "kg|m|m2|unit|yd"}   # approximate street price, optional
notes: ""
```
API (`huntkit.materials`):
- `load(id) -> Material` (dataclass with `.id .name .category .props: dict .confidence ...`)
- `Material.get(key, default=None)`, `Material.require(key)` (raises a clear error if missing)
- `query(category=None, **filters) -> list[Material]`, e.g.
  `query("textiles", areal_density_gsm__lt=150)`
- `all_materials() -> list[Material]`

## 2. FEA (`huntkit.fea`)
- Frame geometry goes in as a YAML/dict of nodes (mm), members (node pairs plus section plus material id)
  and supports/loads. Sections: `tube_round(od, t)`, `tube_rect(w, h, t)`, `flat_bar(w, t)`,
  `composite_tube(od, layup, material_id)`.
- `solve(model) -> Result` with nodal displacements, member forces, von Mises / failure index per
  member, reaction forces, and `max_sf`.
- `load_cases.pack_standard(design_load_kg=68)` gives the standard pack cases (static carry,
  2.5 g drop, side-hill torsion, set-down on one stay, meat-shelf heavy-low).
- `load_standard.ls1_cases()` (HA-LS-1 **rev B**, 2026-11-01): no meat shelf. `meat_shelf_heavy_low` is
  replaced by `meat_straps` (placement `"meat_straps"`: internal-strap anchors + frame-face pressure); frame models
  must provide groups `strap_bottom`, `strap_lumbar`, `strap_mid`, `strap_upper`, `meat_face`
  (`huntkit.fea.pack5200` builds them from geometry.yaml `meat_anchor_z*` / `bag_anchor_low`).
- Report: `report(result, path)` writes Markdown plus PNG plots (deformed shape, utilization).

## 3. Pattern pieces (`huntkit.patterns`)
- `Piece(name, outline: list[(x,y)] mm closed polygon of the SEAM LINE, grain: angle_deg,
  seam_allowance_mm: float | per-edge dict, notches: [(x,y)], drill_holes: [(x,y)], labels: dict,
  quantity: int, mirror: bool, material_id: str)`
- `piece.cut_line()` gives the outline offset by the seam allowance.
- `grade(piece, size_rules) -> dict[size, Piece]`.
- `export_dxf(pieces, path)` writes AAMA/ASTM-style DXF (layers: CUT, SEW, NOTCH, GRAIN, DRILL, TEXT).
- `export_pdf_tiled(pieces, path, paper="letter"|"a4"|"a0")` gives true-scale tiled pages with a
  100 mm / 4 in test square, page-match marks and an assembly map.
- `nest(pieces, fabric_width_mm, grain_constraint=True) -> Marker` gives `.length_mm .efficiency`;
  `marker.export_pdf/dxf`.
- Additions (2026-11-04, backward compatible): `develop_ruled_surface(..., resample=False)` keeps the caller's
  point correspondence; `develop_region(surface_fn, polygon_uv, spacing) -> FlatMesh` flattens any doubly curved
  region by least squares (`.strain_stats()` area-weighted principal strain, `.map_uv()` carries seams/marks to
  the flat; edge targets are on-surface arc lengths, Richardson-corrected, since 2026-11-05);
  `flatten_mesh(V3, tris, rest_length=None)`; `InternalLine(kind="cut_inside")` goes on the DXF CUT layer / SVG cut
  group; `export_pdf_tiled(..., compress=True)` and `marker.export_pdf(..., compress=True)`.
- Addition (2026-11-05, backward compatible): `nest(..., time_limit_s=None, max_candidates=None, progress=None)`;
  after `time_limit_s` the remaining pieces are placed greedily (never left unplaced while they fit the width).
- Material records may carry `roll_width_mm` / `usable_width_mm` (textiles, laminates, sheet goods); markers
  are nested at the roll width with selvedge = (roll - usable) / 2.

## 4. Camo (`huntkit.camo`)
- `generate(pattern_spec: dict, palette: list[hex], width_mm, height_mm, dpi, seed) -> RGB array`
- Patterns are defined in `designs/apparel/camo/<pattern>.yaml` (layers, scales, shapes, colors).
- Export: tileable seamless repeat PNG/TIFF at print DPI + SVG vector separations + preview.

## 5. Manufacturing (`huntkit.manufacturing`)
- `BOM` from a design YAML: material id, qty, unit, waste factor, cost (pulled from material records).
- `SewingOp(seq, operation, machine, stitch_type ISO 4915 (e.g. 301, 401, 504, 516, 607),
  spi, thread_id, needle, attachment/folder, notes, time_s)`.
- `tech_pack(design, path)` builds the PDF: cover, flats, BOM, pattern list, op sequence, QC
  points, packaging.

## 6. Meat haul and the bag-to-frame joint

Owner, 2026-11-01. Both modes are requirements. The eight B-01 swells over the fairleads are accepted.

Stations, both sides, z in mm: hinge 60, under-strap US1 95, under-strap US2 142, IM1 190,
IM2 330, IM3 520. The bearing face in every mode is the **Sandwich v2 spreader** (BP-06 rev B, owner
2026-11-05): 200 g twill carbon skins on 6 mm ROHACELL 110 IG-F, 6.44 mm thick, 242 × 318 mm at z 112–430,
6 removable PA12 clips on the stays, record `designs/pack_5200/analysis/spreader.md`, build files
`designs/pack_5200/cut/spreader/`. Consumers take its numbers from `analysis/spreader_results.json`
(`chosen`), not from the retired 2.0 mm QI comfort model. The frame under it is the socket-free branch body. The two
38 mm under-straps cinch the bag floor to US1/US2 when the bag is on, and they are the cradle
when the bag is off. IM1 is a meat anchor only until the owner says otherwise. Hook and cam
ratings are still assumptions awaiting a proof test.

| Mode | Required | What the modules share |
|---|---|---|
| `bag_on` | yes | Meat inside the bag. IM1–IM3 cinch it against the spreader. Floor vertical is shared by the hinge pins and the US1/US2 under-straps. |
| `between` | yes, as the bulk method of `bag_on` | Bag swings open on the hinge pins. The under-straps stay cammed. IM2 and IM3 bag hooks released. |
| `bag_off` | yes | Bag off in ≤ 120 s (2 cams + 4 hooks + 2 hinge pins). The under-straps stay on the frame as the cradle. IM1–IM3 cinch the quarter against the spreader. No shelf. |

FEA models keep the groups in §2 (`strap_bottom`, `strap_lumbar`, `strap_mid`, `strap_upper`,
`meat_face`). `meat_face` is the spreader, not the wearer's back. Pattern pieces for B-01 include
the eight accepted swells. The procedure and the safety factors are in
`designs/pack_5200/analysis/meat_haul_modes.md`.

## 7. Cloth simulation (`huntkit.clothsim`, added 2026-11-05, additive)

Batch static cloth simulator. It takes the real flat pattern pieces, sews them in 3D on their seam pairing,
loads them and reports volume, shape, strain, seam line force and frame contact. Owner: structural-fea-engineer.
Method: `docs/research/cloth_sim_methods.md`. Validation and limits: `designs/pack_5200/analysis/cloth_sim.md`.

- **Pieces in** (`PieceSpec(name, edges, map3d, fabric, grain_deg, rest_map=None)`): `edges` = ordered
  `[(edge_name, flat (k,2) mm, X3 (k,3) mm)]`. This is the seam line in the piece's flat frame, with the 3D
  arranged position of the same points. `map3d(flat) -> 3D` places interior points. `rest_map` is an optional
  flat-to-flat panel adjustment. Edges are sewn where their arranged 3D curves coincide within `tol`, which is
  notch-position pairing. `assemble(specs, h, tol, outward_ref) -> (ClothMesh, diag)`. `diag["seams"]` and
  `diag["free_segments"]` must be empty for a closed bag.
- **Fabric** (`fabric(material_id) -> FabricModel`): `k_warp, k_weft` N/mm, `shear` N/mm/rad, `bending` N mm,
  `compression` fraction, `areal_kg_mm2`, `strip_warp/weft` N/mm. These are derived from `data/materials` break
  strengths and the ASSUMPTION elongations in `huntkit/clothsim/fabrics.yaml`. Seam strength
  `seam_strength_n_mm(mat_a, mat_b, thread_id, stitch_mm, stitch)` = min(1.5 or 1.7 × thread break / stitch
  length, `seam_efficiency` × weaker strip strength).
- **Solver** (`Sim(mesh, terms).solve(x0, tol, max_iter, time_cap) -> (x, SolveInfo)`): static equilibrium
  by damped Newton. Terms: `Membrane`, `Bending`, `Gravity`, `DeadLoad`, `Pressure` (p0 + ρ g (z_ref − z)),
  `PressureProfile` (any p(z)), `GasFill` (polytropic contents), `Pins`, `Cables` (`Cable`: elastic
  tension-only, or `T_const` cinched), `FieldContact` (`GapField` from STL samples), `Anchor`.
- **Pack 5200** (`huntkit.clothsim.pack`): `PackModel(scenario)` + `run_case(pm, case)`. Pieces come from
  `designs/pack_5200/patterns_v31.py` `build_body` (read only, cached in `outputs/clothsim/cache/`). The scenario
  YAML (`huntkit/clothsim/scenarios/pack5200_v31.yaml`, `extends:` supported) holds the mesh, solver,
  `panels:` adjustments (`scale_warp`, `scale_weft`, `material`, `*_scale`), `fabric_overrides`, seams,
  contact, attachments, Janssen fill, meat (HA-LS-1 rev B §4.1) and cases. Optional keys (additive, 2026-11-05; absent
  = phase-1 behaviour): `attachments.hinge.doubler_mm`, `attachments.hooks.tab {stations, width_mm}`,
  `attachments.ties {list: [{id, pieces, at [x, z], anchor [x, y, z], mode elastic|cinched, pretension_n, width_mm, via}]}`,
  `contact.crown {enabled, top_z, leg_od, bar_od, bar_aft_mm, spine_od, spine_len}`. Bridled attachments report one
  summed entry (`legs`, `leg_max_n`); the crown reports as `contact.contact_crown`.
- **Outputs** (`python -m huntkit.clothsim.cli run|validate|diff`): `outputs/clothsim/<scenario>/results.json`.
  Per case it holds `volume` (L), `pieces` (strain %, wrinkle area %, mass g), `hot_spots`, `seams`
  (`max_n_mm`, `p95_n_mm`, `strength_n_mm`, `sf`), `attachments` (tension N, SF), `contact` (spreader and
  frame force, footprint touching %), `profile`. It also writes `x_<case>.npy`, `clothsim_<case>.glb` and
  `clothsim_<case>_viewer.html`. The viewer is `huntkit.viz3d`'s; `metrics.chips` / `metrics.subtitle` are an
  optional header added to `viz3d.viewer` here. Units: mm, N, N/mm, L.
