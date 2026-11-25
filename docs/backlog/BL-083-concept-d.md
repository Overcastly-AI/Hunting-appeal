# BL-083 Concept D (tube stays + formed hip pan) with real joints, hip offset freed, B81 lever row

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-080 (concept D), BL-081 (B81, machinery), BL-082
(6061 fatigue, friction, crush, prices) · **Date:** 2026-11-25

Ask (orchestrator): design and check concept D (tube stays + a formed or flat-laser-cut 6061 hip pan that carries the
hip torque as a plate) on the BL-081 basis, with the hip pivot offset as a free variable if the hipbelt interface still
works; cost <= USD 150 per frame with the pan priced on SendCutSend's cited method; body <= 1300 g stretch; a B81 lever
row (hose-band tees, .049 stays with a local doubler, local metal) as a comparison; rank the best three of H1c, B81
levers and D. Don't edit bl077 / 079 / 081, the kit generators or huntkit/manufacturing; don't commit.

## Result (2026-11-25)

Record: [designs/pack_5200/iter2/frame_d/bl083.md](../../designs/pack_5200/iter2/frame_d/bl083.md) / `.json`
(`python -m huntkit.gendesign.bl083_report run`: five stages in their own processes, about 30 min cold; `md` re-writes
the Markdown and screens). Code: `huntkit/gendesign/bl083_concept_d.py` (D83 model on the B81 model, pan rows, 5052
basis, SendCutSend price rule, hose-band clamp rows), `bl083_parts.py` (flat patterns + DXF, STL, cut list, bills),
`bl083_report.py`. The BL-081 global / local checks and `huntkit/fea/tube_solid.py` run unchanged (builder and station
list swapped in for the call). Tests: `tests/test_bl083_concept_d.py`.

- **SendCutSend does not bend 6061-T6** (their 6061 page: "we don't offer bending for 6061"; they recommend 5052). The
  formed pan is therefore **5052-H32** (minimum yield 159 MPa, ASSUMPTION AL5052-MIN). A flat-cut 6061 pan without
  return flanges fails the lumbar push in plate bending, and bolted angle returns make it heavier than B81's lumbar node.
- **D83** = B81's stays / bars / tees / foot + a 5052 .100 tray (face at the BL-055 boss face y -48.55, walls along the
  stays, 25 / 20 mm returns, 4 bends) + a 5052 .100 spine channel under the Ti mount (2 bends) + one 3/4 x .035 strut on
  an M5 rod at z 155. Pan bolts are lateral (along x): the stay holes sit on the neutral axis of fore-aft bending.
  **Strong PASS, min 1.02** (B81's upper-tee wall fatigue, unchanged); pan rows min 1.10 (walls), buckling 1.51
  (0.99 without the strut). **1849.5 g, USD 262.06.**
- **D83-L** (hose-band tees, local metal): **PASS 1.02, 1674.3 g, USD 242.54.** .049 stays were tried: the upper tee
  wall goes to 0.67 (quick check), so they are not a lever on either frame.
- **Hip offset:** the belt fixes it (pin through belt B's centre plate, pad seated on the pan face). Moving the pin aft
  15 / 30 mm saves 26 / 53 g of tray, adds 37 / 74 g of belt EVA and the shorter walls lose margin (0.92 / 0.41). Keep
  the BL-055 / 056 mount and its 67 mm offset; the pan carries it in the walls' plane.
- **B81-L as briefed** (bands + .049 stays + doubler + local): **FAIL 0.70** (upper tee wall), 1774.7 g, USD 199.88
  (.049 tube costs more than .065). **B81-Lb** (bands + local, .065 kept): **PASS 1.02, 1815.6 g, USD 156.76.**
- **No D variant beats H1c on mass (1404.7 g) within the cap; none meets 1300 g.**

| rank | option | Strong | USD | g |
|---:|---|---|---:|---:|
| 1 | D83-L | PASS 1.02 | 242.54 | 1674.3 |
| 2 | B81-Lb | PASS 1.02 | 156.76 | 1815.6 |
| 3 | D83 | PASS 1.02 | 262.06 | 1849.5 |
| - | B81 (reference) | PASS 1.02 | 176.28 | 1990.9 |
| - | H1c | FAIL (two joints) | 164.59 | 1404.7 |
| - | B81-L | FAIL 0.70 | 199.88 | 1774.7 |

Rubric order puts every strong option first; all are over the cap, so mass orders them. On cost B81-Lb is USD 6.76
over, D83-L USD 92.54 over (the SendCutSend pan, USD 126 at qty 1 on ASSUMPTION SCS-PRICE, band 90-126).

### Coupons / proof (pass lines in bl083.json `variants.D83.coupons`)
FB-1 bend coupon (5052 .100, no crack at the SCS radius), BB-D pan-bolt bearing (<= 0.2 mm at 1145 N, ultimate >=
1718 N), HP-D hip pan proof (V 1630 + H 1239 N hold, then 1e4 x 0-859 N), KF-D lateral-hole stay fatigue, CL-1 / CL-B
clamp slip (>= 1201 N wet), CF-1 foot cup, T1-D crown deflection -3.6 mm +/-30 % at 19 in. Proving USD 62.53.

### Open items
1. Orchestrator / owner: no option meets Strong + cap. Lift the cap ~USD 7 for B81-Lb, fix H1c's two joints, or take
   D83-L if a real pan quote (or a batch) comes under ~USD 33.
2. Every strong option carries B81's upper-tee stay-wall fatigue 1.02 (< 1.2): KF-1 / CL-1 coupons before release.
3. SendCutSend quote for the tray / spine DXFs (r, K, price); mill cert for 5052-H32 minimums.
4. Hose bands: torque-tension and wet slip (CL-B) settle ASSUMPTION BAND; upper bands at 3.3 N m.
5. Pan modelled as a grillage; HP-D proof settles the local wall stress at the z 155 bolt (1.10).
6. Interface notes for pack-designer: IM1 loop above the wall (wall beside the stay stops at z 170); belt pad seat on the
   pan face unchanged (190 x 150, 25 mm top return); 8 Ti-mount screws now all used (M5 x 16 through face + spine).
