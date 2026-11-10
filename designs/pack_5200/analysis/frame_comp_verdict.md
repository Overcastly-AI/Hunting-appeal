# Printed-frame competition: judge's verdict

Judge: design-reviewer (independent), 2026-11-10. Rules: [frame_comp/RULES.md](../frame_comp/RULES.md). Standard: HA-LS-1 rev C
([load_standard.md](load_standard.md)). Baseline: [print/frame/PRODUCTION.md](../print/frame/PRODUCTION.md),
[rev_c_verification.md](rev_c_verification.md). Machine-readable: [frame_comp/verdict.json](../frame_comp/verdict.json).
Figure: `outputs/screens/20261110_comp_verdict.png`. Team files were read and re-run, not edited.
Judge scripts and logs (scratch): the session scratchpad `judge/` folder (recheck.py, excl.py, push.py, score.py, plot.py).

## 0. Verdict in one screen

| | |
|---|---|
| **Winner (gate passed, best score)** | **A MONO**: 6.95 / 10. It passes rev C on the release voxel FE. Normalised mass is **−18 g** vs today, not the −20 g against the booked 1063 g it claims (see §2). |
| **Runner-up (gate passed)** | **C ROD**: 6.47. It is by far the lightest (−169 g normalised), but it is an intermediate build (13 pieces, carbon drilling, 56 fastener sets) and it does not look generative. |
| **D SERVICE** | **Gate not met as submitted.** Branch Euler buckling is **0.47** under the rule MONO is held to, and D did not check it. With a branch fix (est. +20 g) it would score 7.40 and rank second. |
| B SEG-2T / E LOOM | Pass, but both are heavier than today (+55 g / +64 g normalised). Their own docs say so. |
| **Hybrid H1 (recommended build)** | Today's branch body re-sized locally in PAHT-CF with D's offset tool, plus A's floors, buckling check and dry z 234 joint, printed at home on the H2S. Body ≈ 745 g at **fatigue 1.25** (judge run). Frame ≈ 1041 g, frame + spreader ≈ 1203 g. **Score 7.47, above every entry.** |
| CORRIE B.2, belt M | Today, dowels booked: **3982.9 g (8.78 lb)**. With A MONO: **3964.7 g (8.74 lb)**. With H1: **≈ 3943 g (8.69 lb)**. With D after the fix: ≈ 3905 g (8.61 lb). With C: 3814 g (8.41 lb). |

## 1. The A vs D discrepancy: resolved

A says a PAHT-CF re-size bottoms out at 767 g with fatigue 1.046. D's PAHT-CF control reached 747 g at strength 1.52 and fatigue 1.26.

**Both pipelines are correct. Neither has a checker bug. The difference is the design parametrisation.**

- **Same checker.** Both use the same allowables (layer FI 88 / 47 / 0.6 × 47, × 0.8, fatigue 0.30, creep 0.40), the same 42 rev C sets (27 crown-bar + 15 IM3), and the same FI99 with clamp and load-patch exclusion (`frame_cg_recheck.summarize_body`).
  - Judge re-run on the released body with D's pipeline: 1.510 / 1.044 / 2.228, and branch buckling 1.495 (A's rule).
  - A's parametric body at scale 1.05 is a near copy, not an exact one: 819.4 g raster against 823.2 g, and 1.508 / 1.040 / 2.219.
- **Cross-check of both bodies with one tool** (judge, D's `solve_fields` + `evaluate`):

| body | raster g | strength | fatigue (own excl.) | fatigue (union of excl. with today's) | fatigue (fixed top-1 % count) | creep | branch buckling L / R (A rule) |
|---|---:|---:|---:|---:|---:|---:|---:|
| today | 823.2 | 1.51 | 1.044 | 1.05 | 1.11 | 2.23 | 1.50 |
| A MONO | 763.2 | 1.28 (A) | 1.05 | 1.048 | 1.09 | 2.23 | 1.27 (A) |
| D PAHT control, as reported | 746.8 | 1.52 | 1.256 | – | – | 2.68 | 1.24 / 1.12 |
| D PAHT control, **fairleads + pads restored** | **769.3** | **1.53** | **1.26** | **1.26** | **1.29** | **2.69** | **1.23 / 1.12** |
| judge push: D tool continued (u_lo 0.85, radius cap 0.45, branches held, fairleads restored every step) | **734.1** | 1.45 | 1.25 | – | – | 2.67 | 1.42 / 1.16 |

- **Not an exclusion artifact.** D's margin survives the union exclusion and the fixed-count measure. The excluded voxel count is 20 978 against 20 919 today.
- **Why A stalls.** A's loop scales seven whole member families uniformly (`frame_comp_A.py:94`, `:450`, `:468-482`). The fatigue hot spot is local: the strut-to-stay junction at z ≈ 150 and the lower sleeve wall at 23 in on the IM3 couple (`20261110_compA_2.png`).
  - To lower one junction, A inflates the whole "low" (+9 %) and "strut" (+6 %) families and thins the branches and mid bar, which pushes load back into the stays.
  - The ±10 % step then oscillates (it4–it6).
- **Why D wins on the same mass.** D's SDF offset grows only the junctions and the upper bar. It thins the feet, branches, mid bar and struts, and still *removes* 14 g from the "low" family.
  - At about the same mass (769 vs 763 g raster), D's geometry has **20 % more fatigue margin** (1.26 vs 1.05).
- **A's statement "a monolithic PAHT-CF body cannot go much lighter" is wrong.** It is a limit of A's parametrisation, not of the material.
- **D's "still falling" is half true.** Continued with deeper thinning, the body converges at **≈ 734 g**, with fatigue stuck at **1.25**. What sets FI99 there sits in regions the interface rules keep (sleeve bores and bushing seats, pawl housing, pivot). Fatigue no longer limits the mass. The thinning caps and keep-outs do.
- **Floors the judge's 734 g body still breaks.** The mid bar is at r_eq 4.2 mm (A's printability floor is 5.0 mm) and the foot balls are at 6.8 g (today 15.7 g; boot fit and hinge-pin boss). Restoring both adds about 13 g.
- **What a correct PAHT-CF re-size achieves.**
  - With today's keep-outs: **≈ 745 g body (−78 g)**, strength ≈ 1.45, fatigue ≈ 1.25, creep ≈ 2.67, branch buckling ≥ 1.16.
  - It still passes if CA-1 lands as low as a 0.245 fatigue ratio (18 % below the record 0.30).
  - Not run: thinning the sleeve outer surface to the 3.6 mm wall floor could reach about 710–730 g.
  - If CA-1 proves 0.40, A estimates 686 g. That figure is unconverged, and branch buckling was not re-checked.

## 2. Mass bookkeeping, normalised

**Finding: today's 1063 g omits the z 234 dowels.** Team B is right.
- `frame_mass_production.json` is 823.2 + 217.4 + 22.0 = 1062.6 g.
- The 217.4 g non-body figure comes from `frame_branch.pack_numbers` ("dowels are gone", `frame_branch.py:162`).
- The 8 × Ø5 × 70 mm carbon dowels weigh 17.0 g, plus about 1.5 g of MMA: **18.5 g in total**.

Three teams then subtract dowels that were never booked:
- **A** (`frame_comp_A.py:425-429`): −8.5 g dowels and −3 g MMA. A also forgot to add back the 4 dry dowels it keeps.
- **D** (`frame_comp_d.py:620`, `:627`): −18.5 g.
- **E** (`frame_comp_e.py:751`): −21.5 g.

The fixed-part allowances also differ:
- C uses 275.0 g (`frame_comp_C.py:714-715`, from `frame_light2.CROWN` / `PIVOT`).
- Every other team uses today's 239.4 g (1062.6 − 823.2), which excludes dowels and also excludes the crown corner wraps (about 26 g, probably missing from today's record too).

**Common basis used here:**
- Every fixed interface is booked at 239.4 g: crown with the rev C fix, rack, pawl, bushings, Ti mount, inserts. The P-1 bondline adds no mass (DECISIONS 2026-11-09).
- Spreader 162.3 g.
- Every dowel, bolt, nut, boss and printed feature an entry physically has is counted.
- Pack = 2739.5 g + frame + spreader. That is the CORRIE B.2 belt M figure without the booked frame + spreader of 1225 g.

| entry | team-claimed frame g | normalised frame g | frame + spreader g (lb) | Δ vs today (dowels booked) | CORRIE B.2 M g (lb) | correction |
|---|---:|---:|---:|---:|---:|---|
| today | 1063 | **1081.1** | 1243.4 (2.74) | 0 | 3982.9 (8.78) | +18.5 dowels + MMA |
| A MONO | 1043.3 | **1062.9** | 1225.2 (2.70) | −18.2 | 3964.7 (8.74) | +19.6: 4 dry dowels 8.5 and MMA 3 were deducted from a basis without them; the 0.4 g NON_BODY difference is removed |
| B SEG-2T | 1136.2 | **1136.2** | 1298.5 (2.86) | +55.1 | 4038.0 (8.90) | none: B booked it right |
| C ROD | 947.6 | **911.9** | 1074.2 (2.37) | −169.2 | 3813.8 (8.41) | −35.6: fixed parts at 239.4 instead of 275.0. Printed parts are shell estimates, ±15 % (±54 g) |
| D SERVICE | 965.0 | **982.9** | 1145.2 (2.52) | −98.2 | 3884.7 (8.56) | +18.5: dowels deducted that were never booked |
| D + branch fix (judge est.) | – | ≈ 1002.9 | ≈ 1165.2 (2.57) | ≈ −78 | ≈ 3904.7 (8.61) | +20 g of branch section for buckling ≥ 1 (§3) |
| E LOOM | 1124.1 | **1145.0** | 1307.3 (2.88) | +63.9 | 4046.8 (8.92) | +20.9: dowels and MMA deducted that were never booked |
| H1 hybrid (judge) | – | ≈ 1040.9 | ≈ 1203.2 (2.65) | ≈ −40 | ≈ 3942.7 (8.69) | body ≈ 745 (§1) + A's joint 56.5 (bosses 25.6 + Ti bolts and nuts 22.4 + 4 dry dowels 8.5) |

On this basis A's z 234 joint is **+38 g over today's bonded dowels** (56.5 g vs 18.5 g), not +11 g. ASSUMPTION: A's bosses (25.6 g) are hand estimates. They are in neither the STL nor the FE.

## 3. Margins resting on unsourced or borrowed numbers

The flip point is the coupon shortfall at which a pass becomes a fail (margin × ratio < 1).

| entry | margin | rests on | coupon | flips if the coupon comes in below |
|---|---:|---|---|---|
| A | body fatigue 1.046 | PAHT-CF fatigue 0.30 at 1e5 (published PA12-CF 0.25–0.32 at 1e6, Siebert 2025; 0.40 Stratasys) | CA-1 | 0.287 (**−4.4 %**) |
| A | joint fatigue 1.22 | 12 mm washer bearing in a side-access nut trap, 0.3 fatigue. **No boss-bending or prying check** (B's similar joint is governed by boss bending at 1.03 with twice the bolts per stay). If the bare nut bears (31.7 mm² instead of 89.3 mm²), the margin is 0.43. | CA-5 | −18 % on bearing; boss bending not computed |
| B | joint fatigue 1.03 | boss bending across the layers at 0.3 × 0.8 × 47 MPa, prying 1.25 | CT-B3 | −3 % |
| C | joint 1.12 (bar-pin bearing) | CFRP pin bearing 300 MPa ult (ASSUMPTION A1, below the 500 MPa plate record) | RC-2 | 268 MPa ult (**−10.7 %**). C states the same breakeven. |
| C | upper bar FPF 1.13, stays FPF 1.24 | Rock West wall modelled at 0.845 mm (vendor 1.0) | RC-1 | conservative |
| D | body fatigue 1.12 | **MJF** PA12 Basquin lower bound (Avanzini 2022) applied to **SLS**. D's own Goodman check puts SLS about 5 % lower (26.2 vs 27.7 MPa at 1e6) → ≈ 1.06 | D-F1 | 19.6 MPa at 1e5 (**−10.7 %**) |
| D | body strength 1.21 | 48 MPa datasheet. Avanzini's measured MJF lot was 43 MPa → 1.08. At 40 °C the part is above the 27 °C Tg onset, and the 0.8 knock is borrowed from FDM. | D-C2 | 39.7 MPa dry-equivalent (−17 %) |
| D | creep 1.37 | rupture ratio 0.35 at 40 °C 8 h (ASSUMPTION), above Tg | D-K1 | 0.255 (−27 %) |
| D | **branch buckling, not checked by D** | judge: A's rule (K 1, E × 0.55 hot × 0.7 creep = 635 MPa, P_cr ≥ 1.5 × factored). Lower branch **0.47**, upper branch 0.76. Without the creep factor: 0.68 / 1.09. With K 0.7: 0.97. | none | **fails now** |
| D | load path | the body is 0.45 × today's torsion stiffness (0.42 × hot). The beam model that feeds crown legs (1.12), spreader (1.09) and fairlead loads assumes the stays do not change. Not re-run. | D-T1, T1 deflection | unknown |
| E | strength 1.07 (lumbar column, interlayer) | ILSS 14 MPa dry (published 2.8–34) × 0.6 | E-2 | 13.1 MPa (**−7 %**) |
| E | fatigue 1.006 | CFRP FI 0.5 rule borrowed for printed CCF (no endurance data), on a printer with no X-CCF datasheet | E-5 | **any shortfall** |
| H1 | body fatigue ≈ 1.25 | PAHT-CF 0.30 | CA-1 | 0.24 (−18 %) |

The joint (A's CA-5) is now the weak link of H1, not the body.

## 4. Gate

The gate: rev C passes, and every governing assumption is tied to a coupon.

| entry | rev C (judge's reading) | assumptions tied to coupons | gate |
|---|---|---|---|
| A MONO | pass. Body re-verified by the judge (fatigue 1.048). Joint by hand calculation. | yes (CA-1 … CA-5) | **pass** |
| B SEG-2T | pass (1.03 joint) | yes (CT-B1 … B5) | **pass** |
| C ROD | pass. Judge re-run reproduces 1.116 / 1.121 / 1.135 / 1.741 and 947.6 g. Beam level plus hand calculations; knuckles have no FE; spreader on the 20 mm tubes not re-run. | yes (RC-1 … RC-6) | **pass** (conditional) |
| D SERVICE | **branch buckling 0.47 not checked**; load-path stiffness assumption not checked | partly (none for buckling) | **not met as submitted** |
| E LOOM | pass at beam level (judge re-run reproduces 1124.1 g) | yes (E-1 … E-7), but on a pre-sale platform | **pass** (marginal) |

## 5. Score (RULES weights)

Sub-scores are 0–10:
- **Mass:** 5 + (1243.4 − frame+spreader) / 30, so today = 5 and each 30 g = 1 point.
- **Cost:** $400 → 10, $1000 → 0, at quantity 1, with the $207 spreader included for everyone. A's cost and C's cost left the spreader out (`frame_comp_A.py:542-548`; `frame_comp_C.py:728-752`). A's one-off $60 coupon programme is removed.
- **Build:** judge's reading of each build sequence for a beginner.
- **Risk:** judge's reading of §3 plus analysis fidelity.
- **Look:** judge's reading of the renders.

| entry | gate | mass 40 | build 25 | risk 15 | cost 10 ($, qty 1) | look 10 | **score** | mass 25 % | PAHT fatigue 0.40 credited |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 hybrid (judge) | (new) | 6.34 | 8.5 | 6.5 | 9.32 ($441) | 9 | **7.47** | 7.75 | 8.33 |
| D + branch fix (est.) | (resubmit) | 7.61 | 9.5 | 4.0 | 5.85 ($649) | 8 | 7.40 | 7.35 | 7.40 |
| D as submitted | **fail** | 8.27 | 9.5 | 3.0 | 5.98 ($641) | 8 | (7.53) | (7.35) | (7.53) |
| **A MONO** | pass | 5.61 | 8.5 | 5.0 | 9.32 ($441) | 9 | **6.95** | 7.29 | 8.18 |
| **C ROD** | pass | 10.0 | 4.0 | 5.0 | 5.22 ($687) | 2 | **6.47** | 5.59 | 6.47 |
| B SEG-2T | pass | 3.16 | 8.0 | 6.0 | 9.42 ($435) | 7 | 5.81 | 6.47 | 5.81 |
| E LOOM | pass | 2.87 | 3.0 | 2.0 | 0 ($3974 incl. printer) | 1 | 2.30 | 2.16 | 2.30 |

**Sensitivity.**
- **Fatigue ratio 0.30 vs 0.40.**
  - At 0.30 (as analysed): A wins among the gate-passers. H1 wins overall, with D after its fix 0.07 behind (within scoring noise).
  - At 0.40, A's body drops to about 686 g and A scores 8.18. A and H1 then pull clearly ahead of D (7.40), which is unaffected because it is PA12. **The winner does not change.**
  - The reverse case: if CA-1 comes in at **0.25**, A (0.87), B (0.86) and E fail. H1 (1.04), C (bearing and fatigue governed by CFRP; PAHT tab 1.02) and D are unaffected, so **C becomes the gate-passing winner** and H1 the build.
- **Mass weight 25 %** (other weights scaled up pro rata): A 7.29 > C 5.59 among gate-passers, and H1 7.75 stays top. **The winner does not change.** C loses the most because its lead is mass.
- **Scoring noise.** H1 vs D after its fix is a near tie: a risk score of 5 for D would put it ahead. The tie-break is the coupons in §6 and whether the owner wants to print at home or order.

## 6. Recommendation for the owner

The owner believes a 3D-printed frame can be strong enough. **It can. Today's printed body already is, and a re-sized one has margin left over.** The honest message on mass is smaller: a printed frame with only dry assembly is near today's mass unless you either (a) let a service print it in one piece, which removes the joint, or (b) go to tubes in printed nodes (C).

1. **Build H1:**
   - A locally re-sized PAHT-CF branch body: D's offset tool, with A's floors (branch and mid bar r ≥ 5 mm, foot ball ≥ 8.4 mm, sleeve wall ≥ 3.6 mm) and the branch-buckling check.
   - Fairleads and pads restored.
   - Printed face-down on the H2S in two segments.
   - The z 234 split made dry with A's 4 Ti M5 nut-trap bolts, after a B-style boss-bending check.
   - Expected: body ≈ 745 g, frame ≈ 1041 g, frame + spreader ≈ 1203 g, **CORRIE B.2 M ≈ 3943 g (8.69 lb)**, body fatigue ≈ 1.25.
   - Cost about $441 per frame with the spreader. Beginner build. Same look as today.
   - The team modules still need to write a re-meshed STL. Engineering task for structural-fea-engineer: about 1 h CPU.
2. **Of the entries as submitted:** MONO wins. CORRIE B.2 M is **3964.7 g (8.74 lb)** on the honest basis, against 3982.9 g today with the dowels booked. MONO's own 3945.1 g figure under-counts by 19.6 g.
3. **Keep D's one-piece SLS option alive** if the owner would rather order than print.
   - Fix the branch buckling (about +20 g), then re-run the beam model with the PA12 body stiffness for the crown legs and spreader.
   - Then order with coupons from the same build.
   - Expected ≈ 3905 g (8.61 lb), at about $649. The hot-day behaviour near Tg is the open risk.

### First coupon tests, in order (rough costs, ASSUMPTION)

| # | test | why first | rough cost |
|---|---|---|---|
| 1 | **CA-1 PAHT-CF fatigue**: XY + Z bars from the owner's H2S, annealed and conditioned; R 0.1, 1e5 at 0.30 then 0.40 × 0.8 × UTS | governs A and B, sets H1's reserve, and unlocks about −50 to −80 g if 0.40 holds | about $20 of filament; $250 for a DIY motorised lever rig, or $1.5–3k at a lab for 12–18 specimens |
| 2 | **CA-5 dry z 234 joint stubs**: 3 static pulls (≥ 1.5 × 2894 N mean) + 1 at 0 → 1543 N × 1e5 on the T5 rig; add a strain or dial check for boss bending | governs H1 and A after the body | about $40 (stubs, Ti bolts) |
| 3 | **CA-3 interlayer** after the 40 °C water soak (Z bars + short-beam blocks) | the FI's interlayer term; also feeds B's boss | about $20 |
| 4 | **CA-4 creep**, 40 °C 8 h dead load | creep is 2.2–2.7, low risk; cheap to close | about $10 |
| 5 | First article: HA-LS-1 T9, T1–T5, T4b with a dial on the branch, T4c at −20 °C, pencil marks across z 234 | system proof | the frame (about $440) + existing rig |
| (D path) | D-F1 SLS PA12 fatigue bars from the ordered build at 40 °C, D-K1 creep, D-C2 hot tensile, D-I1 inserts | D's margins are all on borrowed or assumed data | about $60 of bars + $1.5–3k lab |
| (C path) | RC-2 pin bearing (5 pulls), RC-1 tube bend | C's governing joint | about $120 (one 2 m stick) |

### What would change the verdict

- **CA-1 < 0.287:** A and B fail. C becomes the gate-passing winner. H1 still passes down to 0.24.
- **CA-1 ≥ 0.40:** re-size H1 / MONO to about 686 g or less. The PAHT home print then beats D on mass too.
- **CA-5 fails, or boss bending governs:** use B's 8-bolt flange (verified to 1.03, +17 g vs A's joint). H1 frame ≈ 1058 g.
- **D resubmits with branch buckling ≥ 1 and the stiffness load-path check:** D could take first place on build simplicity, especially if the owner does not want to print.
- **C proves RC-2 ≥ 268 MPa and a CAD body within +15 %, and the owner accepts an intermediate build:** C is about 130 g lighter than H1.
- **A different mass weighting does not change the order of A over C** among the gate-passers, down to 25 %.

## 7. Other findings, by severity

1. **High.** D `result.json` `passes_rev_c: true` was claimed without a branch buckling check (`frame_comp_d.py:643-650` checks only the lower stay). Judge result: 0.47 / 0.76.
2. **High.** The dowel bookkeeping error inflates the savings of A (−19.6 g), D (−18.5 g) and E (−20.9 g) (§2).
3. **High.** D's body stiffness is 0.45 × today's, but the crown, spreader and fairlead margins are copied from the release (`frame_comp_d.py:622-623`). The beam model was not re-run with the softer stays.
4. **Medium.** A's joint check (`frame_comp_A.py:376-389`) has no boss bending or prying. Its bosses are in neither the STL nor the FE.
5. **Medium.** A's conclusion "cannot go much lighter" (`frame_comp_A.md` §0) is an artifact of family scaling (§1).
6. **Medium.** D's control row (`frame_comp_d.py:719-720`) has no fairlead restore. Restored, it is 769 g, not 747 g. D's body also cuts the foot balls by 46 % (boot fit and hinge-pin boss floor not checked).
7. **Medium.** A's and C's unit costs omit the $207 spreader that B, D and E include.
8. **Medium.** C's fixed-part allowance (275 g) differs from everyone else's (239.4 g). Today's record probably omits the crown corner wraps (about 26 g). This affects all entries equally, so the ranking does not change.
9. **Low.** E's 116 g interface allowance is an estimate. It is consistent with its own feature list and is not material to the ranking (E is heavier either way).
10. **Low.** Every team's tests pass (A 9, B 6, C 12, E 12, D 6). None of them re-verify the headline margins; they test helpers and closed forms.

## Assumptions (judge)

- ASSUMPTION: the common fixed-part allowance is 239.4 g for every entry; spreader 162.3 g; dowels 17.0 g + MMA 1.5 g.
- ASSUMPTION: D's branch fix is +20 g, from r⁴ scaling of the lower branch (× 1.2 radius) and the upper branch (× 1.07). Not re-solved.
- ASSUMPTION: H1 floors add +13 g over the judge's 734 g run (mid bar to r 5 mm, foot balls to the A floor). The judge's body was not re-meshed or released.
- ASSUMPTION: the score scales (30 g per point; $400–1000) and the build, risk and look sub-scores are the judge's reading, listed in `verdict.json`.
- ASSUMPTION: coupon costs are rough (filament plus the owner's rig, or typical outsourced fatigue pricing).
