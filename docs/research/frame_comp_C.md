# Frame competition, team C (ROD): research

Date 2026-11-10. Direction: bought carbon rods or tubes captured in bolted printed PAHT-CF clamshells, with load transfer by bearing and interlock and no adhesive. Analysis: [frame_comp_C.md](../../designs/pack_5200/analysis/frame_comp_C.md). Rules: [RULES.md](../../designs/pack_5200/frame_comp/RULES.md).

## 1. Stock tubes: what you can actually buy

| tube | OD x ID mm | layup (published) | g/m | price | source |
|---|---|---|---:|---|---|
| **Rock West 46710** (chosen for stays and mid bar) | 20 x 18 (wall 1.0) | inside to outside 0 / 0 / 0 / 90 / 90 / 3K 2x2 twill, UTS50 fibre | 91 (0.401 lb per 2 m) | $111.99 per 2 m (1-9), $100.79 (10-49), $90.59 (50+) | [rockwestcomposites.com/46710](https://www.rockwestcomposites.com/46710.html) |
| Rock West 46710, published CLT values | | Ex 9.18 Msi (63 GPa), X tension 63 ksi (435 MPa), X compression 70 ksi (484 MPa), XY shear 9.06 ksi (62.5 MPa), hoop (Y) tension 23 ksi | | | same page ("for reference only") |
| Easy Composites CFT-RWM-20-17 (backup) | 20 x 17 (wall 1.5) | UD 0 + UD 90, ply count not given; "not designed for torsional loads"; max 80 C | 139 | EUR 28.40 per m (1-4) | [easycomposites.eu 20 mm](https://easycomposites.eu/20mm-roll-wrapped-carbon-fibre-tube-metric) |
| 20 x 18 x 500 3K roll-wrapped (generic) | 20 x 18 | not published | | $15.53 | [carbonkevlarsupply via reach.dog](https://reach.dog/shop/carbonkevlarsupplycom/products/blue-black-carbon-fiber-tubing-20mm-x-18mm-x-500mm-3k-roll-wrapped-glossy) |
| upper bar: custom roll-wrapped OD 22, +-45 twill / UD 0 x 5 / +-45 twill | 22 x 19.9 | special order, like today's crown tubes | 108 (computed) | $30/m at 16 mm scaled with OD (`cfrp_rollwrapped_tube` record) + set-up ASSUMPTION $40 | repo record `data/materials/composites/cfrp_rollwrapped_tube.yaml` |

One 2 m Rock West stick covers both stays (2 x 530 mm) and the mid bar (180 mm). No stock metric tube with +-45 plies was found for the upper bar. The stock 20 x 18 tube fails there in torsion plus bending (margin 0.81), so the upper bar stays a special-order tube.

**Pultruded rods and tubes are not used for any member.** They are all 0 deg fibre. The repo record (`cfrp_pultruded_rod_tube`) and vendors say they are "very weak in hoop and torsion, prone to longitudinal splitting at holes, clamps". Easy Composites says roll-wrapped tubes are stronger in general use than pultruded ([tubes explained](https://easycomposites.eu/learning/carbon-fibre-tubes-explained)). In pultruded profiles the mostly unidirectional fibres "weaken the profiles when used in bolted joints" ([ICCM23 paper 300](https://iccm-central.org/Proceedings/ICCM23proceedings/papers/ICCM23_Full_Paper_300.pdf)). Our joints need pin bearing, shear-out resistance, contact crush and torsion: pultruded tubes fail all four. "Rebar" here means stock roll-wrapped tubes.

## 2. Getting load into a smooth tube without adhesive

| method | data | verdict for ROD |
|---|---|---|
| clamp friction | No published PA-CF on CFRP friction coefficient was found. CF in PA lowers friction against steel by 12-33 % ([Dergipark PA66/CF](https://dergipark.org.tr/en/download/article-file/3308465)). | **Not credited.** Information value only, mu 0.15 (ASSUMPTION). |
| bolt preload in a polymer stack | Viscoelastic creep "is the dominant factor contributing to preload relaxation" ([PMC6862647](https://pmc.ncbi.nlm.nih.gov/articles/PMC6862647)). Polymer joints lose preload, mostly in the first hours. 30 % of bolted joints on elastomer pads came loose ([Nord-Lock](https://www.nord-lock.com/insights/knowledge/2016/bolting-with-plastic-and-composites)). Conical spring washers limit relaxation in CF-SMC at 120 C (same PMC paper). Belleville washers reduce relaxation in CFRP joints ([Uni Siegen thesis](https://dspace.ub.uni-siegen.de/handle/ubsi/2503)). | The cap bolts only keep the caps closed. Every M3 has a Belleville pair. Computed preload loss: 100 % without the pair, 9 % with it (section 3). |
| through pin / bolt in a drilled tube | ASTM D5961: the bearing strength depends on the procedure, the clamp-up and the clearance ([CompositesWorld](https://compositesworld.com/articles/bearing-testing-of-composites)). The repo QI plate record gives 500 MPa. Hot/wet lowers bolted strength in pultruded profiles ([MDPI Materials 18:2936](https://www.mdpi.com/1996-1944/18/13/2936)). | **Used.** Design value 300 MPa x 0.8 = 240 MPa (ASSUMPTION A1, coupon RC-2). This sits below the plate record because the wall is thin, 0/90, and the pin has no clamp-up. |
| notched (filled-hole) strength | The open-hole ratio depends on hole size and laminate. Thin-ply hybrids keep about 0.96 ([Carvelli ECCM20](https://re.public.polimi.it/retrieve/408437a0-c47f-478d-8aff-8c498793beec/Carvelli_conference_ECCM20-2022_Are%20pseudo-ductile%20all-carbon%20hybrid%20laminates%20notch%20insensitive%20in%20open%20hole%20tension.pdf)). Standard QI scaled tests are in [NASA 19930003402](https://ntrs.nasa.gov/api/citations/19930003402/downloads/19930003402.pdf). No 0.5-0.6 figure was found published for this tube. | 0.55 used (ASSUMPTION A2, conservative). Coupon RC-3. Holes go where the moment has decayed (bar tip, stay stub) or on the neutral axis. |
| end bearing, end caps | Compression into an aluminium disc in the boot floor: the 20 mm disc spreads the 1.0 mm tube wall over 314 mm2. | Used at the foot. |
| flats | Grinding flats cuts the 0 deg plies. | Rejected. |

**Key geometric constraint found in this study:** the crown legs telescope inside the stays above about z 170 (15 in torso). A cross pin through the stay at the mid (z 330) or upper (z 520) knuckle would block the leg. ROD therefore uses:
- mid knuckle: integral with a printed **rail** (foot-saddle + mid knuckle, bolted splice at z 205). Stay axial force goes down the rail to the stay end at the foot (Al disc, foot pin at z 20, below the leg).
- upper knuckle: **two 3 mm single-wall radial pins** at z 525, flush with the bore, retained by the cap. They engage the top crown bushing, not the leg.

## 3. PAHT-CF clamp creep

Published PAHT-CF creep data: none. The record values (`creep_modulus_8h_40c_ratio` 0.7, `creep_rupture_8h_40c_ratio` 0.4, Tg 45 C) are study assumptions. The literature confirms that CF improves creep resistance of printed PA12 but gives no compressive creep curve ([Polymer Testing 2023 via DOAJ](https://doaj.org/article/091672c080a8437880cd4238a1ec92e5); [De Gruyter Engineering 2024 review](https://www.degruyterbrill.com/document/doi/10.1515/eng-2024-0084/html)). ROD's numbers (`preload_creep()`):

- M3 Ti at 600 N on a 10 mm penny washer: 8.6 MPa sustained in Z. Creep-rupture margin 0.4 x 37.6 / 8.6 = 1.74.
- Creep shortening of the 8.8 mm flange stack (3 x the 8 h value, ASSUMPTION): 0.045 mm.
- Bare Ti bolt (k 47 kN/mm): the preload is gone (loss 100 %). With a DIN 2093 Belleville pair (about 1.2 kN/mm, ASSUMPTION): **9 % loss**.
- Consequence if preload is lost anyway: rattle and fretting, not strength. No check credits friction. Coupon RC-5 measures it.

## 4. Patents (not legal advice)

- US 10,952,523 (Mystery Ranch, load lifters / crown): crown unchanged.
- US 10,668,965 and the Divergent node family (adhesive-injected nodes on tubes): ROD has no adhesive, no injection ports and no inner spigot.
- KUIU one-piece frame family: ROD is a multi-part bolted tube ladder.
- Bolted tube-and-clamp structures (scaffold clamps, bike seat-post collars) are old art. Cross-pinned tube joints are generic.

## 5. Coupon tests (each governing ASSUMPTION)

RC-1 tube bend and weigh; RC-2 pin bearing (A1); RC-2f bearing fatigue (A4); RC-3 notched tube bend (A2); RC-4 printed knuckle proof (A3, A7); RC-5 clamp creep hold (A5); RC-6 foot-saddle (disc and foot pin). Definitions are in `result.json` and in the analysis doc §6.
