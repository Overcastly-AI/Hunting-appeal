# Frame competition, Team E (FIBRE): continuous-fibre printing research

Owner: structural-fea-engineer (Team E), 2026-11-10. Rules: `designs/pack_5200/frame_comp/RULES.md`.
Use: allowables for `huntkit/gendesign/frame_comp_e.py`. Every number below has a URL. Anything not published is
an **ASSUMPTION** with the coupon test that must confirm it (E-1 to E-7, listed at the end).

## 1. Platforms: cost and availability

| platform | type | build volume mm | price | status | source |
|---|---|---|---|---|---|
| **FibreSeeker 3** (FibreSeek, CFC co-extrusion) | desktop, home | 300 x 300 x 245 | US pre-sale **$3,199** (early bird; $3,499 list); Kickstarter $2,699 | pre-sale opened 2026-09-15 (US); ship date **not stated** | [3dnatives 2026-09-11](https://www.3dnatives.com/en/fibreseeker-3-presale-launch-07092026/), [3DPrint.com 2025-09-08](https://3dprint.com/320477/fibreseeker-3-the-worlds-first-continuous-fibre-3d-printer-for-the-consumer-launches-on-kickstarter/) |
| FibreSeeker 3 consumables | X-CCF continuous carbon, X-CGF glass; FFF PLA/PETG/PC/PA/PA-CF | | X-CCF $55 per 500 m (record) | | [Fabbaloo](https://www.fabbaloo.com/news/fibreseeker-3-brings-continuous-carbon-fiber-3d-printing-to-the-personal-desktop-market), record `onyx_ccf_markforged.yaml` |
| Markforged Mark Two | desktop industrial | 320 x 132 x 154 | $17,490 | sold | [MatterHackers](https://matterhackers.com/store/l/markforged-mark-two-3d-printer) |
| Markforged FX10 | industrial | 375 x 300 x 300 | quote only | sold | [Markforged FX10 blog](https://markforged.com/resources/blog/introducing-fx10-our-most-versatile-industrial-3d-printer-for-the-factory-floor), [aniwaa](https://www.aniwaa.com/product/3d-printers/markforged-fx10/) |
| Markforged FX20 | industrial | 525 x 400 x 400 | quote only | sold | [Hawk Ridge](https://hawkridgesys.com/blog/announcing-fx20-the-new-3d-printing-system-from-markforged) |
| Anisoprint Composer A3 | desktop industrial | 460 x 297 x 210 (sources disagree) | about £19.5k; listed **discontinued** at one reseller | uncertain | [top3dshop](https://top3dshop.com/product/anisoprint-composer-a3-3d-printer), [Daemon3D](https://daemon3dprint.com/main/anisoprint-composer-a3.html) |
| Bambu Lab | | | | **no continuous-fibre printer found**; X2D / H2D print chopped-fibre filaments only | [CompositesWorld X2D](https://www.compositesworld.com/products/bambu-labs-dual-nozzle-x2d-3d-printer-supports-fiber-reinforced-filaments) |
| Service (Markforged) | per cm3 | | Mark Two CCF **$3.00 / cm3**, Onyx $0.25 / cm3 (university in-house rate, not a commercial bureau) | | [U Minnesota Anderson Labs](https://cse.umn.edu/andersonlabs/3d-printing-service) |
| Service (Markforged bureau) | | | quote only | Mark3D StrongParts (UK) | [Advanced Engineering UK](https://www.advancedengineeringuk.com/en/news/mark3d-uk-launches-strongparts-3d-printing-bureau-at-advanced-manufacturing-show-64064) |

9T Labs and Continuous Composites are industrial (compression-moulded preforms / robot cells); no public price or
retail service found, and 9T Labs' consolidation step is a mould, which RULES.md does not allow.

Build volume decides the split: the frame is 540 mm tall. No listed machine fits it in one piece (FX20 525 mm, and
a 540 x 254 mm part does not fit the FX20 bed diagonally either). Every route needs at least two segments.
ASSUMPTION (owner-buyable route): FibreSeeker 3, two segments of at most 300 mm.

Ownership note: Markforged was acquired by Nano Dimension in April 2025 ([aniwaa FX20](https://www.aniwaa.com/product/3d-printers/markforged-fx20/));
a reported sale to Stratasys is unconfirmed.

## 2. Material data (published)

| property | value | source |
|---|---|---|
| CCF tensile strength, modulus (UD coupon, ASTM D3039) | **800 MPa, 60 GPa** (older sheet 700 MPa, 54 GPa) | [Mark Two datasheet](https://www.cad.at/wp-content/uploads/2022/05/Mark-Two-Datasheet.pdf), [composites datasheet](https://3dverkstan.se/wp-content/uploads/2018/07/markforged_composites_datasheet.pdf), [3D Hubs Markforged](https://www.3dhubs.com/s3fs-public/Markforged.pdf) |
| CCF compressive strength (D6641) | **320 MPa** (older), 420 MPa (newer) | [composites datasheet](https://3dverkstan.se/wp-content/uploads/2018/07/markforged_composites_datasheet.pdf) |
| CCF flexural (D7901) | 540 MPa, 51 GPa (older 470) | same |
| Onyx tensile at break / modulus | 30-37 MPa / 2.4 GPa; density 1.2 | [Knowde Onyx TDS](https://www.knowde.com/stores/markforged/products/onyx), [Onyx MDS](https://3dp.seas.harvard.edu/files/2023/01/OnyxMDS.pdf) |
| Anisoprint CCF composite | up to 860 MPa at 1.4 g/cm3 | [top3dshop CFC PETG](https://top3dshop.com/product/anisoprint-cfc-petg-1-75-mm-750-g) |
| FibreSeek X-CCF | "up to 900 MPa" (marketing, no test method) | [3DPrint.com](https://3dprint.com/320477/fibreseeker-3-the-worlds-first-continuous-fibre-3d-printer-for-the-consumer-launches-on-kickstarter/) |
| Real-part tension (mixed Onyx / CCF "isotropic" layers) | **165 MPa** UTS, far below the 800 MPa all-fibre coupon | Pertuz et al., *Int. J. Fatigue* 130 (2020) 105275, [HAL](https://hal.archives-ouvertes.fr/hal-02307802), [record](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_journals_2310279775) |

The repo record `data/materials/composites/onyx_ccf_markforged.yaml` holds these (E1 60 GPa, Xt 800, Xc 320, Onyx
40 / 30 MPa XY / Z, densities 1.2 / 1.4). The analysis reads them from there.

## 3. Fatigue

- Pertuz et al. 2020 (Mark Two, nylon matrix, 0 deg carbon): S-N in the **finite-life region only**; Basquin
  A = 206 MPa, b = -0.039 (from a [Scribd copy](https://www.scribd.com/document/800046151/gth); not confirmed
  against the publisher). A flat slope, typical of fibre-dominated 0 deg tension.
- A 2025 review by the same group states that **no endurance-limit data** exist for AM nylon composites with
  continuous fibre ([MDPI Eng 6(10) 277](https://mdpi.com/2673-4117/6/10/277)). Failure modes: fibre tearing, matrix
  cracking, fibre / matrix pull-out.
- Onyx (short fibre) S-N at R = 0.1 exists ([Frattura ed Integrita Strutturale 2023](https://doaj.org/article/24bc6cbb40834938834b6ef9bfe871cf)) but not for the interlayer.
- **ASSUMPTION used:** HA-LS-1 CFRP rule (fibre FI <= 0.5 at 1.6 g, 1e5) for fibre-direction stress; the PAHT
  matrix rule (0.3) for every matrix / interlayer / bearing stress. Coupon E-5 (stay-section bend fatigue) and E-4
  (bearing fatigue) confirm.

## 4. Interlayer (Z) weakness and hot/wet

- Printed continuous-fibre composites have poor interlaminar bonding and high voids ([Springer PAM 2021](https://link.springer.com/content/pdf/10.1007/s40964-021-00187-1.pdf)).
- ILSS: Caminero et al. 2018 (Mark Two carbon / glass / Kevlar in nylon, short-beam shear): carbon best, Kevlar worst,
  ILSS falls with thicker layers ([Polymer Testing 68:415, record](https://peeref.com/works/5814949)); numeric values
  were not retrievable. Published printed CF/PA6 values span **2.8 to 34 MPa**, with 28.0 MPa for a well-consolidated
  process ([ResearchGate, voids study](https://www.researchgate.net/publication/339300170_3D_printed_continuous_CFPA6_composites_Effect_of_microscopic_voids_on_mechanical_performance),
  [pultruded CF/PA6 commingled 33.9 MPa](https://www.researchgate.net/publication/358775983_Continuous_fibre_composite_3D_printing_with_pultruded_carbonPA6_commingled_fibres_Processing_and_mechanical_properties)).
  **ASSUMPTION 14 MPa dry** (half of 28), coupon E-2.
- Moisture: nylon-based prints absorb up to 10x more water than PLA, flexural modulus down by up to 60 % after 7 days
  immersion ([PMC8587952](https://pmc.ncbi.nlm.nih.gov/articles/PMC8587952)); moisture attacks the fibre / matrix
  interface and the filament-to-filament bond. **ASSUMPTION matrix hot/wet 0.6** on every matrix-dominated
  strength (record `modulus_40c_wet_ratio` 0.6). Fibre-dominated stays at the HA-LS-1 0.8.

## 5. Routing limits

- Fibre lies **only in the layer plane** (record note). Minimum fibre-loop width **2.9 mm**, minimum fibre-reinforced
  projecting feature **3.8 mm** ([Markforged: minimum fiber feature sizes](https://markforged.com/blog/threading-the-needle-with-ease)).
  Minimum reinforced part height 1.125 mm for carbon ([Aarhus design guide](https://ase.au.dk/fileadmin/www.ase.au.dk/Filer/Laboratorier_og_vaerksteder/Komposit-lab/3D_Print/Composites_Design_Guide_V1-2.pdf)).
- No published minimum turn radius for Eiger; academic path-planning work treats it as tow-width dependent
  ([A*STAR 2025](https://oar.a-star.edu.sg/storage/3/3q8mr8o203/toolpathtocfrp-comstr2025.pdf)). **ASSUMPTION 10 mm** at
  the stay / bar corners (coupon E-7).
- Concentric fibre threads narrow geometry as one continuous path; holes are reinforced with concentric rings
  ([Markforged composites intro](https://markforged.com/resources/learn/design-for-additive-manufacturing-plastics-composites/3d-printing-composites-introduction/3d-printing-composites-with-markforged)).
- Only one continuous fibre per part on some machines ([Berkeley X7 protocol](https://me.berkeley.edu/wp-content/uploads/2025/05/Markforged-X7-Protocol-2024.pdf)).

**What this means for today's body.** The released branch body is curved out of the frame plane (y span 73 mm:
lumbar pan, sleeve offsets). Printed flat (layer normal y), a member that rises through y is cut by the layers, so
its fibre could only run in short pieces; the branches that curve in y cannot carry continuous fibre. Printed on
its side, the stays could follow their y profile, but then every stay / bar junction becomes a joint. Team E
therefore re-topologised to a **planar ladder** (the frame.yaml v2 geometry, straight stays) printed flat, so
flange layers run the full member length and concentric rings run round each window without a cut.

## 6. Patents (screen, not legal advice)

- Mystery Ranch US 10,952,523 (load lifters): crown, top bar and lifters unchanged (DECISIONS 2026-11-01).
- Markforged process family, US 9,126,365 / US 9,579,851 / US 10,040,252 / US 9,156,205 ([Google Patents US9579851](https://patents.google.com/patent/US9579851),
  [US10040252](https://patents.google.com/patent/US10040252), [uspto.report 9,156,205](https://uspto.report/patent/grant/9,156,205)):
  claims cover the printer and the printing method. Using a commercial machine is covered by its sale; nothing
  here claims a pack frame. Attorney review before production, as for every entry.

## 7. Coupon tests that close the ASSUMPTIONs

| id | test | pass |
|---|---|---|
| E-1 | ASTM D3039 / D6641 on flat-printed X-CCF flange coupons, dry and conditioned (40 C / 85 % RH) | B-basis >= 544 MPa tension, >= 166 MPa compression (design values incl. 0.85 part factor) |
| E-2 | ASTM D2344 short-beam shear, 0.125 mm layers, dry and conditioned | >= 14 MPa dry, >= 8.4 MPa wet |
| E-3 | ASTM D5379 in-plane shear; matrix Z tension | >= 20 MPa; >= 30 MPa |
| E-4 | ASTM D5961 pin bearing, M5 hole with 3 fibre rings; 1e5 cycles at 0.3 x static | >= 60 MPa dry, no elongation > 2 % |
| E-5 | 4-point bend fatigue, 400 mm stay section, C1 moment x 1.6, R 0.1, 1e5 cycles; then residual | survives; residual >= factored C2 |
| E-6 | sleeve ring crush with the 18 mm UHMWPE bushing; 1e5 cycles at 1.6 g bushing force | >= 1.0 x factored C8 load |
| E-7 | fibre ring round a 10 mm radius stay / bar corner, T-pull | >= factored corner force |
