# Pack 5200 hipbelt: fit and load-transfer redesign (study, 2026-11-08)

Owner: pack-designer. **Status: proposal. Nothing in the released geometry, YAML or patterns has changed**
(`build_geometry.py`, `geometry.yaml`, `panels.yaml`, `patterns_v31.py` were only read).

Owner request: *"The hip belt needs improvement. To better fit the hips. It takes all the load."*

- Research (cited): `docs/research/hipbelt_fit.md` (cited below as **[HR §n]**).
- Model: `huntkit/gendesign/hipbelt.py`. Hip forms from ANSUR II: `analysis/hipbelt_anthro.yaml`.
- Concepts, results, figures and pieces: `designs/pack_5200/concepts/hipbelt_concepts.py` writes
  `concepts/hipbelt_results.json`, the PNGs and `outputs/hipbelt/hipbelt_B_pieces.dxf` / `_M_1to1.pdf`.
  `concepts/hipbelt_render.py` writes the Cycles render. Tests: `tests/test_hipbelt.py` (10 pass).

Units: mm, N, kPa, g internally; inches and ounces in brackets.

---

## 0. Summary for the owner

**What is wrong with today's belt**
1. **The wing is a straight strip, so it wraps as a cylinder.** The hips are a cone: ANSUR II median 4.4 deg for men
   and 10.0 deg for women, steeper on smaller waists [HR §1.2]. The 0/5/10 deg cant snap tilts the straight wing but
   cannot make it conical. A straight strip only ever makes a cylinder. On a woman's hip, or a lean man's, the
   belt bears on its **bottom edge** and **gaps at the crest**, which is the "gap at the crest" complaint. Peak
   pressure is 64 kPa (women's median) and up to 78 kPa, against a 48.6 kPa equal-discomfort limit.
2. **The lumbar pad is flat on a rigid centre plate** while the low back is hollow above the sacrum. Lumbar peaks are
   46–60 kPa.
3. **Every size has 72 % of the hip padded.** The ASIS ("hip pointers") stays about 227 mm apart whatever the waist
   size, so on the smaller users in each size the wing tip sits **on the ASIS** (5 of 16 hip forms, up to 21 mm past
   it). That matches the "bruised hip pointers, Leukotape" reports.
4. **Sizes 26–42 in miss 13.5 % of ANSUR II men** (above 42 in). S starts below the 5th-percentile woman.
5. **"It takes all the load" is true by design, and the belt has to work hard.** R-07 puts 80 % of 68 kg on the
   hips: 534 N (120 lb), or 854 N at the 1.6 g walking peak. The rev C bag CG (205 mm aft) adds a **316 N** fore-aft
   push into the lumbar at a 19 in torso (413 N at 15 in). With skin-textile friction μ 0.3, holding that without
   slip at the walking peak takes about **300 N (67 lbf) of belt tension**, 210–530 N across the 16 forms. On the
   current 1:1 pull that is the hand force too. At the pressure limits the current belt holds only **58 % of that
   need** (median), or 0.92 of the 1 g load. That is the slip-and-crank cycle users describe.

**Recommendation: concept B, "CONE CUT + DUAL DENSITY + 2:1"** (+44 g, +1.3 h build, +$6.80 material):
- wings cut as a **developed cone per size** (7/6/5/3/2 deg, S to XXL). That is a 3–5.5 mm bow in the flat
  pattern: the same sewing, a curved binding;
- the **cant snap deleted** (a fixed joint), which also clears US 12,588,748;
- a **terraced lumbar wedge** (three 5 mm EVA steps, removable, out for XXL) and a dual-density 150 x 150 lumbar;
- **taller wings at the crest** (150/145/105 mm) and a perforated-EVA **crest-relief** comfort zone;
- a **2:1 forward pull** that halves the hand force;
- a **soft tip**: the HDPE stops 25 mm short so the tip stays behind the ASIS;
- **5 sizes, 27–44 in**, re-centred on ANSUR II.

Results over 16 ANSUR II hip forms (8 per sex, 28–42 in):

| | Current | **B** | change |
|---|---|---|---|
| Wing peak, median / worst | 61.5 / 78.0 kPa | **50.8 / 56.5** | −17 % / −28 % |
| Lumbar peak, worst | 60.5 kPa | **45.4** | −25 % |
| Mean contact pressure, median | 26.5 kPa | **22.4** | −15 % |
| Contact area, median | 731 cm² | **849** | +16 % |
| Hold at the pressure limits (share of the 1.6 g need), median / worst | 0.58 / 0.34 | **0.72 / 0.64** | +24 % / +88 % |
| Hand pull to hold, median | 306 N (69 lbf) | **189 N (42 lbf)** | −38 % |
| Wing tip vs ASIS, worst | 21 mm onto it | **3 mm behind** | fixed |
| ANSUR II coverage men / women | 86 / 96 % | **94 / 97 %** | |
| Belt body mass (same method) | 165 g | **209 g** (+44 g, +1.6 oz) | pack 3496 → ~3540 g |

The cheapest useful step is **concept A** (cone cut + terraced wedge, same layup and sizes): +1 g, +0.4 h. It gets
most of the women's gain (median peak 64 → 50 kPa), but the tips still hit the ASIS and the pull stays 1:1.

**The biggest single slip lever is friction, not shape.** At μ 0.5, the belt holds 1.09–1.18 times the walking-peak
need within the pressure limits (B), and needs about half the tension. A grippy (silicone-dot) face is in B, but
it is **not credited** until test HB-2 measures it, because the shirt-on-skin interface may slip first [HR §2].

---

## 1. The belt today (from the source of truth)

| Item | Today | Source |
|---|---|---|
| Wings | Straight tapered trapezoid, root 140 → tip 95 mm (5.5 → 3.7 in), tip corners R20; length S 186 / M 223 / L 259 / XL 296 mm, from padded length = **72 % of hip circumference** (ASSUMPTION) − 140 mm lumbar | `build_geometry.py` `HIPBELT_*`, `patterns_v31.build_hipbelt` (H-01..H-05), `panels.yaml` grading |
| Layup | 330D shell (H-01) / spacer-mesh face (H-02) / **EVA 45C 6 mm** load (H-03, inset 8) / **EVA 30C 5 mm** comfort (H-04, inset 6) / **1.0 mm HDPE** (H-05, inset 12, "carries load to the iliac crest", fit/FEA ASSUMPTION) | same |
| Shape / cant | Flat (cylindrical) wing; **0/5/10 deg 3-position snap** where each wing joins the centre plate | DESIGN.md §5.2 |
| Pivot | Single centre **Ti pin in a bonded Ti insert** on the lumbar pan at `hipbelt_pivot` (0, −48.1, 120); free roll ±8 deg with an elastomer centring bushing; PA66-GF30 centre plate + POM latch, tool-free swap | DESIGN.md §5.2, `geometry.yaml` |
| Lumbar | "Firm 2-stage": 160 x 140 shell / grippy spacer face, EVA 45C 8 mm stage 1 + **removable EVA 45C 8 mm stage-2 "wedge"** 130 x 90 (flat in the BOM) | H-06..H-09 |
| Sizes | S 26–30, M 30–34, L 34–38, XL 38–42 in hip at the crest | `HIPBELT_SIZES` |
| Closure / pull | 50 mm webbing + one 50 mm side-release (HIP family), 1:1; 25 mm stabilizers to z 60 | weight rows |
| Pockets / tabs | 2 x 0.97 L pockets (#8 zip, 330D, S 113 / M 150 / L–XL 180 mm wide), rifle-boot tabs both wings, SH-05 camo tip shard | `panels.yaml` HP-01/02 |

**Mass.** `geometry.yaml → weight`: **hipbelt (M) 334.3 g (11.8 oz) = 9.6 % of the 3495.6 g pack, the third-largest
group** after the frame (1062.6 g) and the main bag (365.5 g). It is made of 191.7 g computed soft goods (wings,
lumbar, pockets, rifle tabs), 97.6 g hardware (50 mm webbing + buckle, pocket zips, stabilizers) and 45 g centre plate
+ latch (ASSUMPTION). The belt body alone (H-01..H-09) is 163.3 g. Benchmark: SG 3-Piece Belt 12.8 oz / 363 g [HR §3].

Nothing in the repo analyses the belt body, the centre plate or the cant snap. The FEA covers the Ti pivot and its
mount (§6).

---

## 2. Model (`huntkit/gendesign/hipbelt.py`)

A transparent comparison model, not a substitute for a pressure mat (HB-1).

1. **Hip forms (ANSUR II).** For each 2 in band of crest-level circumference and each sex, the median subject
   (n 62–680 per band) gives waist breadth / depth / circumference, hip breadth and buttock depth. The belt-level
   section is a **superellipse whose exponent is solved so its perimeter equals the measured circumference**
   (n ≈ 2.6–2.9). Below the crest the section widens laterally by the lateral cone slope and posteriorly by the
   posterior slope (ASSUMPTION: all the buttock-depth gain is behind). ASIS half-distance is 113.5 mm (CT, n 200),
   scaled by bicristal breadth (ASSUMPTION).
2. **Belt = developable band.** A wing cut on a cone of half-angle β lies on the body with its generators leaning
   in by β. The stiffened band is in-plane stiff (hoop stiffness E t / r², HDPE 1100 MPa x 1 mm). It can only rotate
   away the share k / (k + k_hoop) of the cone mismatch; foam and tissue compression take the rest across the belt
   height. That share is about 0.3 at the crest, so **an HDPE-stiffened straight wing cannot conform to a cone.**
3. **Loads (HA-LS-1 rev C).** 68 kg; hips 80 % (R-07); bag CG 205 mm aft at z 550; overturning couple reacted at the
   yoke and the lumbar pad: H = 68 g x 0.205 / (yoke z − 120) = **413 / 316 / 256 N at 15 / 19 / 23 in**. Wing line
   load q = T κ (hoop tension x section curvature: highest at the lateral crest), lumbar = H / width + T κ.
4. **Pressure across the height:** Winkler foundation. Foam layers (secant modulus = record `compression_25pct_kpa`
   / 0.25) in series with a tissue column (60 kPa; 25 mm, or **12 mm over the crest**, ASSUMPTION; as `spreader.py`).
   Closed-form full or partial (triangular) contact.
5. **Slip:** wedge + Coulomb. Each element pressed by N on a surface widening downward at α holds
   N (tan α + μ) / (1 − μ tan α) vertically. **μ 0.30** (ASSUMPTION, low end of 0.27–0.71 [HR §2]); 0.50 sensitivity.
6. **Criteria** [HR §1.4]: mean ≤ **16 kPa** (occlusion), wing and lumbar peak ≤ **48.6 kPa** (Wettenschwiler eq. 1
   at the 14 kPa shoulder limit). The crest-top is reported against a **30 kPa** watch level (ASSUMPTION), not used
   as a criterion: a belt that fits the cone *should* bear on the crest.
7. **Outputs:** T_req = wing tension to hold 80 % x 68 kg at the 1.6 g walking peak; pressures at T_req with the 1 g
   couple; **"hold"** = capacity at the highest tension that meets the criteria divided by the 1.6 g need (≥ 1 means
   no slip at the walking peak without exceeding comfort limits; x 1.6 gives the 1 g ratio).

**Checks.** The same mass method gives 165.0 g for the current belt body against 163.3 g booked in `panels.yaml`
(test). The section perimeters match the ANSUR circumferences within 1 %. Force balance is checked across the height
(test). A straight wing develops flat (bow < 0.5 mm) and the cone cut develops with 0.0 % strain (test). The modelled
means (20–29 kPa) and peaks (40–78 kPa) are in the range of published belt mats: most static peaks exceed 16 kPa
(Wettenschwiler 2015).

**Limits.** No dynamics (walking is a factor on the vertical load only). No shear stress or skin stretch. The tissue
modulus is generic. A single ellipse-like section (no local bony crest ridge or ASIS bump). The belt sits at the
crest line. Absolute kPa are ±30 % indicative; the **comparisons between belts are what count**.

---

## 3. Results

### 3.1 Pressure (figure 1, laid flat; figure 2, on the hip)

| Form (ANSUR median) | Current: size, T, peak / lumbar / mean kPa, cm², hold, ASIS | B: same |
|---|---|---|
| Female 28 in | S, 209 N, 78 / 60 / 29, 483, 0.34, −4 mm | S, 230 N, 55 / 45 / 22, 612, 0.66, +20 |
| Female 30 in | M, 207 N, 72 / 56 / 27, 552, 0.47, −19 | S, 274 N, 55 / 43 / 22, 633, 0.71, +42 |
| Female 34 in | M, 267 N, 68 / 49 / 26, 611, 0.49, +23 | L, 240 N, 47 / 34 / 20, 789, 0.78, +9 |
| Female 38 in | L, 322 N, 58 / 39 / 24, 747, 0.60, +29 | XL, 295 N, 45 / 28 / 20, 899, 0.78, +17 |
| Male 30 in | M, 276 N, 63 / 47 / 27, 684, 0.55, −21 | S, 360 N, 56 / 34 / 27, 662, 0.64, +40 |
| Male 34 in | L, 306 N, 51 / 42 / 26, 781, 0.62, −9 | L, 321 N, 49 / 28 / 23, 868, 0.74, +13 |
| Male 38 in | L, 415 N, 65 / 37 / 28, 794, 0.60, +37 | XL, 383 N, 51 / 26 / 23, 962, 0.71, +25 |
| Male 42 in | XL, 530 N, 70 / 35 / 31, 877, 0.54, +46 | XXL, 483 N, 56 / 32 / 26, 1067, 0.64, +33 |

All 16 forms are in `hipbelt_results.json → rows`. **By sex:** women's median wing peak goes 64 → 47 kPa, worst
78 → 55, median hold 0.54 → 0.76. Men's median peak goes 61 → 55, worst 71 → 57, lumbar worst 50 → 35, median hold
0.58 → 0.71. B needs more tension for the smaller men in each size (median 325 → 365 N), because the ASIS rule
shortens their wings. The 2:1 more than pays for that at the hand (325 → about 215 N).

**Where the current belt hurts** (figure 1, top row): the bottom-edge band at the sides and the bottom of the lumbar
pad, with the top edge lifted off over the crest. That is the "gap at the crest" and the belt riding down onto the
glutes and hip flexors. **B** (bottom row) bears across the full height. The remaining peaks are at the lateral crest,
where the body curvature is greatest (q = T κ), and are cut there by the taller wing.

### 3.2 Levers one at a time (figure 4, from the current belt; F30 / M34)

| Lever | Effect | Verdict |
|---|---|---|
| **Wing cone β** 0 → 14 deg | F30 peak 72 → **38 at 10 deg** → 46; M34 51 → **43 at 4 deg** → 71 (over-coned: top-edge loading) | **Biggest lever.** Per-size cone, and the best cone differs by about 5 deg between the sexes |
| **Lumbar taper** 0 → 0.20 | F30 lumbar 56 → **26** (at 0.20); M34 42 → **29 at 0.10** → 44 | Second lever. Needs per-size / per-person: **removable terraced wedge** |
| Wing height 120 → 180 mm | M34 peak 57 → 50, hold 0.57 → 0.70; F30 ≈ none | Moderate; taller at the crest only (mass) |
| HDPE inset 4 → 45 mm (narrower stiffener) | flat to 20 mm, then **peaks jump** (M34 69 at 30 mm, 123 at 45) | Keep the stiffener ≥ belt height − 20 mm |
| HDPE thickness 0.5 → 2.0 mm | ±1 kPa | No lever: **1.0 mm stays** (mass) |
| No stiffener | F30 peak 72 → 58 (conforms), M34 mean ↑, crest-top ↑ | Rejected: the load spreads less and the belt rolls |
| Comfort foam (EVA 30C 3/5/8, perforated 6, EVA 45C 5) | ±3 kPa | Foam choice is not the fix; shape is |
| Torso 15 / 19 / 23 in | Lumbar push 413 / 316 / 256 N: lumbar peak +2 / 0 / −2 kPa; T_req ±10 % | Short torsos load the lumbar most |
| Friction μ 0.3 → 0.5 | T_req −45 %, hold 0.62 → 0.96 (C0, M34), 0.71 → 1.09 (B) | **Biggest slip lever**; HB-2 must measure it |

### 3.3 Fit range, ASIS and sizes (figure 5)

- The ASIS sits 70 % (28 in) to 77 % (42 in) of the half-circumference from the spine. **A fixed 72 % padded length
  is too long for small users and too short for large ones.** B sets each wing length so the padded tip ends ≥ 5 mm
  and the HDPE ≥ 30 mm behind the ASIS of the smallest user advised into that size: **S 157 / M 197 / L 232 / XL 266
  / XXL 304 mm** (padded fraction 0.61–0.73).
- **5 sizes, 4 in each, 1 in overlap: S 27–31, M 30–34, L 33–37, XL 36–40, XXL 39–44 in.** ANSUR II coverage men
  86.5 → 93.7 %, women 96.0 → 96.7 %. US hunters are likely heavier than soldiers, so the XXL matters more than
  ANSUR suggests (ASSUMPTION). Exo also uses 5 overlapping sizes [HR §3].
- Cone per size (§4.2): **S 7, M 6, L 5, XL 3, XXL 2 deg.** The developed bow is 4.7 / 5.4 / 5.5 / 4.0 / 3.0 mm:
  easy to ease on a walking foot.

---

## 4. Concepts

All keep the Ti pivot at z 120, the centre-plate interface, pockets and rifle tabs. Masses use the same rule for every
concept (`belt_bom`, size M); hardware deltas are listed. Build hours are **ASSUMPTION** deltas for a beginner on one
walking-foot machine (current belt ≈ 6 h ASSUMPTION). Cost is material only, from the records + 15 % waste.

| | **A: CONE CUT** | **B: CONE + DUAL DENSITY + 2:1 (rec.)** | **C: SWAP WING** |
|---|---|---|---|
| What | Per-size cone pattern (8/6/5/2 deg on today's 4 sizes); cant snap → fixed joint; terraced lumbar wedge; same layup, sizes, 72 % | A + taller crest zone 150/145/105; perforated-EVA crest relief; lumbar 150 x 150 EVA 45C 6 + EVA 30C 6 + wedge; 2:1 forward pull (25 mm, 2 D-rings); silicone-dot grip face; soft tip; 5 ASIS-sized lengths | B, but each wing swaps on the centre plate and comes in **two cones per length**: T (β − 3) and C (β + 4); default C for women, T for men |
| Mass Δ (belt body) | **+1 g** (165 → 166) | **+44 g** (→ 209) | **+68 g** (→ 233; connectors 24 g ASSUMPTION) |
| Build hours Δ | +0.4 h | +1.3 h | +2.5 h |
| Material cost Δ | +$0.1 | +$6.8 | +$14.8 (+ a second wing SKU per size) |
| Wing peak median / worst | 51.3 / 71.6 kPa | **50.8 / 56.5** | 47.6 / 58.9 |
| Lumbar peak worst | 45.2 | **45.4** | 45.5 |
| Hold median / worst | 0.67 / 0.54 | **0.72 / 0.64** | 0.73 / 0.62 (women 0.84 median) |
| Hand pull, median | 306 N | **189 N** | 189 N |
| ASIS, worst | −21 mm (on it) | **+3 mm** | +3 mm |
| Patent check | Cant snap removed (US 12,588,748 cl. 4/15); one HDPE sheet (cl. 14) | as A; webbing 2:1 only (not cord/pulley: US 10,638,827, US 6,609,642); no heat-mould needed (US 2006/0060625 abandoned) | as B; **wing swap connectors not searched**: counsel |

**Not taken forward:** tension wings / split top-bottom pulls (in the model, a 65/35 top share changed peaks by
< 2 kPa); heat-moulding (the owner can't do it at home, and the cone cut gets most of the benefit); a narrower
stiffener; a thicker HDPE.

### 4.1 B in detail (recommended)
- **Wing (HB-W1..W6, figure 3; DXF/PDF in `outputs/hipbelt/`).** Developed cone per size (`hipbelt.wing_flat`,
  `develop_ruled_surface`, strain 0.0 %). Root 150, crest zone 145 (at 45 % of the wing), tip 105 mm. 330D shell,
  spacer-mesh face with silicone-dot print, EVA 45C 5 mm load layer (inset 8), EVA 30C 6 mm comfort layer with a 90 mm
  **perforated EVA 6 mm crest-relief insert** (inset 6), **HDPE 1.0 mm** (inset 10), ending 25 mm before the tip
  (soft tip). The D-ring tab is bartacked inside the stiffened zone.
- **Lumbar (HB-L1..L5).** 150 x 150 bearing pad: EVA 45C 6 + EVA 30C 6 (dual density), spacer face with grip print,
  plus a **removable terraced wedge**: three EVA 45C 5 mm steps, 120 wide, 150 / 99 / 50 mm tall, top-aligned. It
  fills the lumbar hollow (taper 0.10). The user can take it out or flip it (XXL: out). It replaces today's flat
  stage-2 piece.
- **Joint.** Wing to centre plate is fixed; the 3-position snap is deleted. Updated 2026-11-09 (DECISIONS,
  `hipbelt_structural.md`): a stitched ear (plate ear inside the wing root, 1000D doubler each face, 2 rows of 22 x 2 mm
  holes, hand saddle-stitched tex 135); the HDPE floats; the lumbar pad bears on the frame lumbar pan
  (`concepts/corrie.py pad_seat()`), not on the 6061-T6 bow-tie centre plate.
- **Pull.** 50 mm buckle; each side 25 mm webbing anchored on the buckle half, round a D-ring on the wing tip, back
  through the heavy ladder lock (`ladder_lock_25mm_heavy`) on the buckle half, then the pull tail (2:1, efficiency
  0.85 ASSUMPTION). The lock must come after the D-ring: routed the other way it holds the full T (slip SF/req 1.01).
  Corrected 2026-11-09 per `hipbelt_structural.md` section 0 item 4 and DECISIONS 2026-11-09.
- **Sizes.** S 27–31 / M 30–34 / L 33–37 / XL 36–40 / XXL 39–44 in; cones 7/6/5/3/2 deg.

### 4.2 How the cones were chosen
For each size, β was scanned 0–12 deg and the value chosen that maximises the **worst** hold over the ANSUR forms
advised into that size (both sexes); ties were broken toward the women's forms. The best β per form is about 10 deg for
women at 28–34 in and 3–5 deg for men, and falls with waist size for both. A single cone per size is a compromise:
that is the case for C.

---

## 5. Recommendation

**Adopt B** for the next prototype belt (pattern-maker to draft from `recommended_pieces`, manufacturing-engineer to
re-sequence). B fixes all three fit faults (cone, lumbar, ASIS), halves the pull force, and covers more people. Its
44 g is 1.3 % of the pack. If the owner wants zero mass, **build A now** and add the 2:1 and soft tip later. Keep
**C** as the "universal fit" upgrade for women once B is validated: it adds +0.08 to the women's median hold.

---

## 6. Structural check with existing numbers (no new FEA) and hand-offs

| Item | Existing number | New load from B | Status |
|---|---|---|---|
| **Ti pivot + mount** | Factored drop at the 80 % hip share **1600 N**; mount SF/req **8.6** static, fatigue **19.7** (`generative_design.md`, `bag_attachment.md`) | Belt tension is a closed hoop: it does not load the pivot. B does not change the vertical path | OK |
| **Pivot fore-aft (lumbar couple)** | Not stated in the pivot rows | The lumbar push **H = 413 N at 15 in** (1 g) passes lumbar pad → centre plate → pivot → lumbar pan; x 2.5 g = **1.03 kN fore-aft** with the 1.6 kN vertical | **Flag → structural-fea-engineer:** confirm the pivot / mount / pan check includes this horizontal reaction |
| **Centre plate (PA66-GF30, 45 g ASSUMPTION) + POM latch** | **No analysis in the repo** | Carries H and the two wing tensions. B's fixed wing joint sees T up to **~480 N** (XXL, μ 0.3), limit x 2.0 = **~1.0 kN per side**, fatigue 1e5 cycles 0 → T | **Flag → structural-fea-engineer** (new part check; conditioned PA66 values) |
| **HDPE wing stiffener** | 1.0 mm, "FEA/fit check ASSUMPTION" (DESIGN.md) | Taller (150 mm); soft-tip D-ring tab anchors in the stiffened zone at T | Flag: tab pull-through + HDPE creep at sustained T (record: HDPE creeps) |
| **50 mm side-release buckle** | Break 1500 N (record) | Sees T ≤ 530 N → limit 2.0 x T ≤ 1.06 kN < 1.5 kN | OK |
| **25 mm ladder lock (2:1 running end)** | Slip **300 N** (record) | Sees T/2 ≤ 265 N; margin only 1.13 at XXL | **Flag → materials-engineer:** specify a 25 mm cam/ladder with ≥ 400 N slip, or check T at XXL |
| **25 mm D-ring** | No record | Carries T (two legs of T/2) ≤ 530 N, limit 1.06 kN | **materials-engineer:** add a record (ASSUMPTION 5 g, $1) |

---

## 7. Pocket implications (for the loadout study, not edited here)

The concurrent loadout study (`docs/research/hunting_loadouts.md`, `analysis/loadout_study.md`, `loadouts.yaml`) may
propose hipbelt pocket sizes. Constraints from B:
- **Room per wing** (wing − 30 mm root/stabilizer − 25 mm soft tip and D-ring − 10 mm): **S 92, M 132, L 167, XL 201,
  XXL 239 mm**. Today's pockets are S 113 / M 150 / L–XL 180 mm, so **S–L pockets shrink by 13–21 mm** and XL/XXL can
  grow. A rangefinder-sized pocket (~150 mm) fits from L up; S and M need a shorter or taller pocket.
- Cut the pocket face to the **developed (curved) wing outline**, or gusset it so it does not straighten the cone.
- Keep pockets off the soft tip and the 2:1 D-ring. Pocket height over the wing is 105–145 mm.
- Pocket mass sits outside the stiffener and is carried by the belt. ASSUMPTION: ≤ 300 g per pocket has a negligible
  effect on pressure (< 2 % of the 534 N hip load).
- **Conflict with the loadout study (read 2026-11-08, `analysis/loadout_study.md`):** IMP-5 proposes taller pockets
  with a 200/160 x 130 mm face (175 mm interior) so a 160 mm phone fits. On B that length fits only XL and XXL (room
  201 / 239 mm). On S–L it would run over the soft tip and the D-ring, and on S/M over the ASIS. Options: (a) let the
  pocket length grade with the wing and put the phone on the shoulder strap for S/M; (b) a pocket taller than it is
  long (130 x 120) does not take a 160 mm phone either; (c) keep the pocket on the stiffened zone and accept that the
  phone rides elsewhere. **IMP-3 bottle holster (1 L ≈ 1 kg, one side):** mount it on the stiffened zone behind the
  crest and in front of the stabilizer, not on the soft tip. 10 N on one wing is under 2 % of the hip load, but it
  pulls that wing down and out, so it needs a lower tie to the wing. Pack-designer and the loadout owner to reconcile.

---

## 8. Visuals (SCREENSHOTS)

1. `outputs/screens/20261108_hipbelt_1.png`: pressure laid flat, current vs B, S/M/M/L forms (women 30 and 34 in, men 34 and 38 in).
2. `outputs/screens/20261108_hipbelt_2.png`: pressure painted on the hip (3D), current vs B, female 30 in / male 34 in.
3. `outputs/screens/20261108_hipbelt_3.png`: B flat pattern pieces to scale (graded wings S–XXL vs today's M; M wing stack; lumbar set).
4. `outputs/screens/20261108_hipbelt_4.png`: lever sweeps (cone, lumbar taper, height, stiffener width / thickness, foam).
5. `outputs/screens/20261108_hipbelt_5.png`: sizes vs ANSUR II and the hip cone vs waist size.
6. `outputs/screens/20261108_hipbelt_6.png`: Cycles render, B on the mannequin (male 34 in, size L), rear 3/4.
7. `outputs/screens/20261108_hipbelt_7.png`: Cycles render, side.

Build files (scratch, not released): `outputs/hipbelt/hipbelt_B_pieces.dxf` (wings S–XXL + lumbar set),
`outputs/hipbelt/hipbelt_B_pieces_M_1to1.pdf` (tiled 1:1, size M).

---

## 9. Owner decisions

- **OD-HB1:** adopt **B** for the next prototype belt (or A now, B later, or C).
- **OD-HB2:** **5 sizes** S 27–31 / M 30–34 / L 33–37 / XL 36–40 / XXL 39–44 in (today 4 sizes, 26–42).
- **OD-HB3:** **delete the 0/5/10 deg cant snap.** It cannot make a cone, and it is close in function to
  US 12,588,748 claims 4/15. The cone goes into the pattern.
- **OD-HB4:** silicone-dot grip print on the belt faces, **credited only after HB-2**.
- **OD-HB5:** accept **+44 g** (pack about 3540 g / 7.80 lb).
- **OD-HB6:** keep R-07 at 80 %, knowing that holding 80 % of 68 kg at a walking peak needs about 300 N of belt
  tension at μ 0.3. In practice the shoulders will take more than 20 % on the steepest, heaviest pack-outs, and the
  2:1 makes it easy to cinch.

## 10. Prototype tests (add to BUILD_PLAN when adopted)
- **HB-1 pressure map.** Current vs B on 3 testers (a woman about 30 in, men about 34 and 38 in), 68 kg sandbag
  (150 lb), belt tension measured with a luggage scale on the pull tab. Pressure film or an FSR strip
  (ASSUMPTION: a 6–50 kPa range film exists; materials-engineer to source). Pass: B peak ≤ current − 15 %, no ASIS
  contact.
- **HB-2 friction.** Sled test (ASTM D1894-style) of the face fabric with and without the silicone print against
  polyester and merino base layers, dry and sweaty. Pass to credit μ ≥ 0.45.
- **HB-3 slip / settle.** 30 min hike, 68 kg, tension set to T_req; mark the crest on the belt and measure the creep.
  Pass: ≤ 15 mm (ASSUMPTION).

## 11. Assumptions (tagged in the code)
μ 0.30 (0.50 sensitivity); tissue 60 kPa over a 25 mm column, 12 mm over the crest; posterior cone = all the buttock-
depth gain; ASIS scaled by bicristal breadth; 30 kPa bony watch level; shell hoop stiffness 30 N/mm; foam-only band
bears over h − 16 mm; tension split moment arm 0.35 h; 2:1 efficiency 0.85; lumbar load centroid at the crest; current
belt ≈ 6 h to build; hour deltas; D-ring 5 g / $1; grip print 5 g / $3; cant-snap detents 6 g; swap connectors
12 g each; 15 % cutting waste; padded tip 5 mm and HDPE 30 mm behind the ASIS.
