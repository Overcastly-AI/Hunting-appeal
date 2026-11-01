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
