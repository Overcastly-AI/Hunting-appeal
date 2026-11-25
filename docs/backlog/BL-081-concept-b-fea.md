# BL-081 Concept B tube-ladder frame: detailed FEA (frame_concepts.md section 8)

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-080 (concept B), BL-082 (6061 fatigue, crush,
friction, prices) · **Date:** 2026-11-25

Ask (orchestrator): run the section 8 checks of `designs/pack_5200/iter2/frame_concepts.md` on concept B with real
joints (global model, lumbar cross tube holes, stays at the crown bushings, pan-free load path, upper tee clamps with the
pawl at 1001 / 1334 N, the real two-angle hip bracket, foot cups, IM1-IM3 and the 8 fairleads on metal, 150 N cinch
cycles); printed tees on the honest PAHT hot/wet basis in bearing / compression only; fix shortfalls lightest and cheapest
first inside the USD 150 cap; coupons with pass lines; STLs, jigs, cut list. Mid-task: use the BL-082 records.
Don't edit bl077 / bl079, the kit generators or huntkit/manufacturing; don't commit.

## Result (2026-11-25)

Record: [designs/pack_5200/iter2/frame_b/bl081.md](../../designs/pack_5200/iter2/frame_b/bl081.md) / `.json`
(`python -m huntkit.gendesign.bl081_report run`, about 5 min with the FE caches, 15 min cold). Code:
`huntkit/gendesign/bl081_concept_b.py`, `bl081_local.py`, `bl081_parts.py`, `bl081_report.py`; new solver
`huntkit/fea/tube_solid.py` (P2-tet solid submodel of a tube with through-holes, patches and clamps; verified against
Heywood, beam bending / torsion and Roark in `tests/test_tube_solid.py`). Tests: `tests/test_bl081_concept_b.py`.

- **Strong: PASS, min margin 1.04** (stay wall under the upper tee: fatigue (preload mean + walking cycle)); fatigue minimum 1.04, on the
  BL-082 basis (Yahr mean curve + Goodman: R 0 S_max(1e5) 190.9 MPa, Kf = Kt, no preload credit, wet mu 0.15).
- **But B as drawn in BL-080 does not work.** Its 1.02 relied on rigid joints and printed tees that carried everything.
  With real joints: the single cross tube could not take the hip stand-off torque (V x 67 mm = 110 N m factored) through
  bolt couples across a 1 in tube (bearing 0.95, fatigue 0.49); 1 x .049 holes failed fatigue (0.86-0.93); printed tee
  halves in the clamp preload path are ruled out (BL-082), and a 1/8 backer bends to 0.26. **B81** fixes these:
  twin 1 x .065 lumbar rungs (z 90 / 150) on .090 6061 gusset pairs, printed saddle plugs for the fore-aft load, a hip
  post of two 1-1/2 angles tied to both rungs (torque becomes tie axial load), 6061 half-shell clamps (1-1/4 x .125,
  sawn) with 1 x 1/4 backers at z 330 / 520, crush sleeves in all 18 through-bolts, 1 x .065 tube throughout.
- **Mass 1969 g (4.34 lb) body**, +956 g vs the BL-080 booking,
  +551 g vs H1c and +906 g vs H1 (frame body + hip fixings).
- **Cost USD 176.28 per frame: over the USD 150 cap** (shipping USD 18 with every piece <= 36 in;
  proving USD 66.56).
- T1 prediction at 150 lb (crown elastic deflection vs the lumbar block): 2.5 / 3.6 /
  5.3 mm at 15 / 19 / 23 in, band +/-30 %. Torsion 22.9 N m/deg
  = 8.4 x H1. Buckling margin 1.92.
- Spreader (`spreader.evaluate`, sw110c7d on the B81 supports): sheet passes (FPF 1.87, fatigue
  1.63); skin peak 14.00 kPa sits on the 14 kPa comfort limit
  (flagged, not a strength row).

| # | kind | margin | governing row |
|---|---|---:|---|
| 1 | strength | 1.32 | bars: member strength (beam, all cases) |
| 1 | fatigue | 5.79 | lumbar L-gussets: fatigue at the bolt holes |
| 1 | joint | 3.10 | M5 A2-70 through-bolts: shear at each wall (gussets, hip ties) |
| 2 | strength | 2.83 | rung z150 x-22 hip tie bolt: static (bearing / net section) |
| 2 | fatigue | 1.27 | rung z150 x-22 hip tie bolt: fatigue 1e5 x 0-1.6 g |
| 3 | strength | 1.89 | stay z135 gusset bolt L: static (bearing / net section) |
| 3 | fatigue | 1.15 | stay z135 gusset bolt L: fatigue 1e5 x 0-1.6 g |
| 3 | joint | 11.70 | stay-top bushing (z 460-530, free tube end): bore ovalisation at limit vs leg clearance |
| 4 | strength | 1.75 | spreader sandwich local (bone patch) |
| 4 | fatigue | 1.63 | spreader sheet fatigue (FI <= 0.5 at 1.6 g) |
| 5 | strength | 1.13 | stay wall under the upper tee at limit (clamp + IM3 loop + couple + beam) |
| 5 | fatigue | 1.04 | stay wall under the upper tee: fatigue (preload mean + walking cycle) |
| 5 | joint | 1.20 | tee clamp z 520: slip (axial + torque about the stay) |
| 6 | strength | 1.90 | front angle leg: plate bending under the mount tipping couple |
| 6 | fatigue | 1.44 | front angle leg: fatigue at the mount holes |
| 6 | joint | 5.21 | tie bolts (M5 A2) tension |
| 7 | strength | 1.65 | T4c 122 cm drop on one foot: stay end axial (estimate) |
| 7 | fatigue | 1.30 | foot cup outer cheek: pin bearing fatigue |
| 7 | joint | 2.08 | US1 float cradle on the hinge pin (489 N factored) |
| 8 | strength | 6.86 | IM3 z 520 (loop under the upper tee, bag-on hook case): stay ring + local stress |
| 8 | fatigue | 5.09 | IM3 z 520 (loop under the upper tee, bag-on hook case): fatigue |
| 8 | joint | 1.24 | float design / misuse IM3 eye 559 / 1142 N |
| 9 | fatigue | 24.50 | static-cinch cycles 150 N x 1e5: clamp micro-slip (fretting) criterion |

### Coupons / proof (pass lines in bl081.json `coupons`)
- **CL-1**: clamp slip: 6061 half-shells + 1 x 1/4 backers + 2 x M5 A2 on a 120 mm offcut of 1 x .065, bare tube; dry / wet / wet after 24 h at 40 C under preload / -15 C, n 5 each (BL-082 spec, tube record). Pass: minimum wet slip load >= 1201 N at the upper-tee torque (1.2 x the larger of the pawl half-load 1000.5 N and the factored tee force 439 N); no tube dent > 0.1 mm.
- **BB-1**: bolt bearing: 1 x .065 offcut, M5 + crush sleeve between two .090 gusset strips, pulled along the tube on the rig (come-along + crane scale), n 3. Pass: hole elongation <= 0.2 mm at 1105 N (largest factored gusset-bolt force) and ultimate >= 1657 N.
- **HB-P**: hip post proof: Ti mount on the two post angles, ties to two rung offcuts held in the gusset plates on the rig; load the pin with V 1630 N (+ H 1239 N) through a lever, hold 2 min. Pass: no permanent set > 0.2 mm at the pin, no hole elongation, tie spacers undamaged; then 1e4 cycles 0 -> 870 N (walk V) with no crack (dye check).
- **OV-1**: fit-up: upper tee torqued on the stay top with the crown leg and bushing inside; pull the leg with a spring scale; then hang 1415 N aft on a 25 mm loop under the tee. Pass: leg slide force <= 20 N at full torque and under the loop load; feeler gauge >= 0.3 mm radial at the bushing mouth.
- **KF-1**: notched tube fatigue (BL-082 rule: B fatigue margin 1.04 < 1.2): 1 x .065 offcuts with an M5 crush-sleeved through-bolt, 4-point bending on the T5 crank rig, R 0.1, n 3. Pass: no crack (dye check) after 1e5 cycles at 1.2 x the walk bore stress of the worst stay hole (nominal 49 MPa x 1.2 at the hole fibre).
- **CF-1**: foot cup crush: printed cup + 38 x 38 foot plate + TPU pad in the vise / on the rig. Pass: no crack at 4.0 kN (2 x C4 2001 N); record crush load (T4c estimate 17.9 kN ends in local crush).
- **SC-1**: static-cinch: 150 N x 1e4 cycles (T5 rig) on a webbing loop under a tee on a stay offcut. Pass: no slip mark movement, re-torque angle < 10 deg (preload retention >= 0.9).
- **PL-1**: saddle plug: printed plug in a rung offcut pressed on a stay offcut sideways. Pass: >= 1626 N without crack (1.5 x the largest factored plug force).

### Open items
1. Orchestrator decision: B81 is strong but heavy (1969 g vs H1c 1404.7 g) and over the cap
   (USD 176.28). Options: BL-083 mass/cost levers on B81 (hose-band tee clamps about -150 g, local
   metal pickup -USD 18, .049 stays with a local doubler about -60 g), or move to concept D (formed pan carries the
   hip torque as a plate) / stay on H1c.
2. Fatigue minimum 1.04 < 1.2: KF-1 notched tube coupons (BL-082 rule) before release.
3. Spreader skin pressure 14.00 kPa at the US2 corner relief: back-system owner to check the rail on the round stays.
4. ASSUMPTION prices (1-1/4 x .125 tube, 1 x 1/4 flat, crush-sleeve tube) need quotes.
5. Deltas for the manufacturing-engineer and the kit generators (not edited here) are in bl081.md section 9.
