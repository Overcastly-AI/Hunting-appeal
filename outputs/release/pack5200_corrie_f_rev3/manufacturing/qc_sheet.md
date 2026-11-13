# CORRIE F rev 3 (door D2) - 5200 cu in hunting pack bag: QC sheet, release tests, defects

## In-line and final checks

| ID | Stage | Check | Method | Pass | Frequency |
|---|---|---|---|---|---|
| QC-01 | Print | Test square | ruler on 00_PRINT_FIRST and on one page per print run | 100.0 +/- 1.0 mm both ways | every print run |
| QC-02 | Incoming | Fabric weight and width | cut 100 x 100 mm, weigh 0.01 g; tape the roll width | gsm within +/- 5 % of the record; width >= usable_width_mm | every roll |
| QC-03 | Cutting | Piece size and cut-outs | lay the pattern on the cut piece | +/- 1 mm on pieces < 300 mm, +/- 2 mm on larger; windows / slots / slits present and clean | first piece of each lay + 1 in 10 |
| QC-04 | Cutting | Notches, grain, webbing length | visual; tape | notch 6 mm (never past the seam line); grain within 2 deg of the arrow; webbing +/- 2 mm, ends sealed | first of each + 1 in 10 |
| QC-05 | Sewing | Stitch density | count stitches over 25.4 mm | body 8, light 10, box-X 7 SPI; +/- 1 | start of each shift / each op set-up |
| QC-06 | Sewing | Tension balance | cut a swatch seam open | lock mid-stack, no loops on either face | each set-up |
| QC-07 | Load points | Box-X and bartacks | visual against SK-1; count | full rectangle + both diagonals, start / end overlap >= 10 mm, stitch count >= load table, no skipped stitch, needle hole not torn | 100 % |
| QC-08 | Assembly | Seam match | notches at both ends of every 50 mm | notch offset <= 2 mm; seam end mismatch <= 3 mm; allowance 12 +/- 1 mm | 100 % |
| QC-09 | Assembly | Door zip | run both sliders 10 x end to end; look at the corners | no snag, no wave > 3 mm at the R 55 corners, tape not caught, stops at the hinge band | 100 % |
| QC-10 | Assembly | B-27 ports | pull the guy through at 45 deg; look inside | 20 mm lap closes flat; both ends bartacked; facing follows the crease at z 631 | 100 % |
| QC-11 | Hardware | Hardware fitted | count against the BOM; threading as SK-7 | every lock threaded the right way (pull test by hand), carabiners gate-in, cord lock holds | 100 % |
| QC-12 | Final | Width | tape across the widest point, bag packed full | <= 394 mm (15.5 in) (owner limit) | first article + 1 in 10 |
| QC-13 | Final | Volume | fill with 10 mm foam balls / litre jug method, collar rolled 3 times | owner limit 85 L +/- 3 L (82-88 L, 5200 cu in). EXPECTED on the sewn bag: 81.9-84.0 L (fine-mesh closed volume, corrie_f_body.md 13.5), so a reading of 81.9-82.0 L is the design, not a sewing fault: record it and tell the pack-designer (BL-040 m-17) | first article |
| QC-14 | Final | Mass by kit, PRIMARY fabrics (the set you build) | 1 g scale, bag empty, kit by kit | base 1211 g (42.7 oz), as hunted 1515 g, meat trip 1720 g, each +/- 3 % (= ledger on the team B basis 1147 / 1429 / 1625 g + the primary pattern delta of each kit, costing.md). Alternate-fabric bags: the ledger values | every bag |
| QC-15 | Final | No hook-and-loop, coil zips only | visual | zero hook-and-loop anywhere (owner: quiet bag) | 100 % |
| QC-16 | Final | Camo use | visual | camo only on B-02u, SH-07, SH-01b, FP-b, B-29f, A1-d (accents) | 100 % |
| QC-17 | Final | Thread ends, seals | visual | ends <= 3 mm, no open webbing ends, no burnt fabric | 100 % |
| QC-18 | Final | Labels | visual | ID label with rev 3 + date, size / crown kit, load-limit card (53 kg frame meat, RD-02) | 100 % |
| QC-19 | Final | Kits complete | count | base / as-hunted (lid, B-28 per kit, scope pod) / meat-trip (WX, B-24, liner) bags each complete | 100 % |
| QC-20 | Final | Fit on the frame | hook to a frame or the fit jig: hinge pins, IM eyes through B-12 ports, guys through B-27 | every eye reaches its port without strain; door opens fully; hinge eyes on the z 60 pins with the floor seam 25 +/- 3 mm below the pin centre (already proven by HE-FIT before cut; this confirms the batch) | first article + 1 in 25 |

## Physical tests that gate release (no load point is sewn on a carrying bag before its test passes)

| ID | Test | Gates | Pass / fail | Source |
|---|---|---|---|---|
| MT-1 | 25 mm box-X bartack proof at the BL-010 per-row loads | every 25 mm box-X on IM1-IM3 and US1/US2 | 5 of 5 hold 908 N (IM) and 5 of 5 hold 1080 N (US) for 1 min, 2 of 2 IMC hold 908 N, no broken stitch | test_register.csv |
| MT-2 | meat-strap hook proof per strap (BL-010) | IM free-end hooks | 5 of 5 G-hooks hold 645 N and 5 of 5 carabiners hold 910 N for 1 min, gates close | test_register.csv |
| MT-3 | 25 mm cam buckle slip at the BL-010 per-row loads, dry, wet and cold | IM / US cams | mark moves < 3 mm at 908 N and at 1080 N, 5 of 5, in each of dry / wet / cold | test_register.csv |
| PT-1 | IM3 bag carabiner on the sewn T3 tongue, per-row proof (BL-010) | IM3 carabiner on T3 | 5 of 5 hold 2553 N for 60 s, gate closes after, no visible set | test_register.csv |
| PT-2 | T3 tongue on the 70 mm B-17 tab on a B-01 swatch (BL-010 load) | T3 on the 70 mm B-17 tab | 5 of 5 hold 2553 N, no stitch break, no laminate tear | test_register.csv |
| PT-3 | HE hinge eye on B-18 + B-01 + B-05 floor seam, sewn as op 4.05 (HE-ONE / HE-PIN), no binding | HE eye on B-18 (no binding) | 5 of 5 hold 1530 N 60 s: no stitch break, no Hypalon or laminate tear, B-18 still in the floor seam, the eye still open (no row across it) | test_register.csv |
| HE-FIT | hinge eye 1:1 dry fit on a printed z 60 fairlead (eye on the pin, neck in the throat) | hinge eye on the z 60 pin, 1:1 dry fit before PT-3 and before cut (BL-041 X-2, DECISION HE-PIN) | pin centre 22-28 mm above the floor seam line; box top clear of the cheeks; neck alone in the 18 mm throat; eye points up (no fold-down) | test_register.csv |
| TL-1 | guy + crown-strap toggles in the 38 mm B-25 sleeve on the real crown bar, 494 N | B-25 38 mm sleeve + guy and crown-strap toggles on the real crown bar at 494 N (BL-041, crown_tube_guy_loop.md) | 5 of 5: (1) holds 494 N 60 s, toggle does not pull through or crack, no broken stitch; (2) no crackle; (3) gauge at 494 N within 1.15 x the straight line through the 100-300 N readings, no knee; (4) ovalisation at the LOOP CENTRE (bore gauge, BL-043 m-7) <= 0.40 mm at 494 N (basis A 0.39, B 0.2, C 0.005 mm, all at the loop centre); (5) out-of-round after unloading <= 0.02 mm more than before; (6) no crush mark, whitening or resin crack at 10x, tap test clean; the cold sample holds | test_register.csv |
| PT-5 | guy ladder lock + tri-glide keeper slip | guy lock + tri-glide keeper | slip < 5 mm over 10 cycles | test_register.csv |
| PT-6 | B-24 float stand-off link | B-24 float link | 5 of 5 hold 1410 N, no box-X break, gate closes | test_register.csv |
| LL-H | heavy 25 mm ladder lock slip at 432 N, dry, wet and cold (guys, W1-W3, B-28) | heavy 25 mm ladder lock slip at 432 N (1.5 x 288 N), dry, wet and -20 C: guys, W1-W3 and the B-28 crown straps (the B-28 slip gate since BL-031) | slip < 5 mm, 5 of 5, in each of dry / wet / cold at 432 N (covers the W 338 N proof); a fail in any condition: tell the pack-designer (record fallbacks: aluminium ladderlock) | test_register.csv |
| SEW-F | box-X fatigue on the lever rig: 25 mm box-X loops, 1e5 cycles 44 -> 442 N (R 0.1) | box-X fatigue (ASSUMPTION SEW_FAT 0.40 x box strength): IM end loops (S1), US eyes (S6), belt tabs (H1) | 3 of 3 run-outs to 1e5 at 442 N, no broken stitch, then hold 1080 N 1 min (a 2 of 3 result: run 3 more, pass with 5 of 6) | test_register.csv |
| T9 | loaded CG (+ 15 in, 30 kg meat check); CORRIE F rev 3 items in rows T9-R3a..d (BL-038 split) | loaded CG on the first article (rev C basis); its rev 3 items are the T9-R3a..d rows below (BL-038 split) | bag CG <= 205 mm at z <= 590; meat <= 190; tall <= 185; rev 3 items: rows T9-R3a..d | test_register.csv |
| T9-R3a | T9 rev 3 (a): port guys hold the S-kit top, meat CG at 15 in | rev 3 (a): B-27 port guys hold the S-kit top, CG at the S kit (BL-030) | meat CG <= 190 mm aft (record against 179.3 mm) | test_register.csv |
| T9-R3b | T9 rev 3 (b): crown strap cinch force and retention (CROWN_PRE_N, MU_LID) | rev 3 (b): B-28 crown strap cinch force and retention | after the walk >= 40 N, or the lid still seated on the full top (report both values) | test_register.csv |
| T9-R3c | T9 rev 3 (c): crown strap free length (ROLL-PATH, TORSO-LIN) | rev 3 (c): B-28 crown strap free length per crown kit (cut = longest path + 40 mm spare + 2 grips, BL-039) | S kit full: path <= 968.1 mm (cut 1068.1 - 2 x 50 mm grip tail; sim 928.1 mm); L kit 6-day: record against the sim's 438.8 mm | test_register.csv |
| T9-R3d | T9 rev 3 (d): sewn lid mass and seat (LID_SLIDER5_G, LID_THREAD, LID-SEAT) | rev 3 (d): sewn B-29 lid mass and seat | lid 47.8 g +/- 5 g (ledger); lid edge on the hinge-band seam, camo caps over the blades | test_register.csv |
| FS-O5 | ULTRA 200X 50 mm strip tensile (C-5 / O-5) | alternate fabric gate: ULTRA 200X 50 mm strip (floor / frame side) | mean >= 1840 N/50 mm, minimum >= 1195 N/50 mm | test_register.csv |
| B-28 slip | B-28 crown strap on its heavy ladder lock: covered by LL-H at 432 N (BL-031 dropped the 20 mm gate; 25 mm strap on ladder_lock_25mm_heavy) | release of this package | LL-H pass | corrie_f_body.md 15.6 / 16 |
| PORT-1 | B-27 port mock-up: hose from above 1 min with the guy pulled at 45 deg; 100 N guy pull through the lap; gloved use of the guy ladder lock where it is sewn: on its LLT tab at B-22, INSIDE the hinge band (DECISION GUY-LOCK-IN, BL-040 M-5), reached through the open roll top | release of this package | no water inside; lap stays closed at 100 N; 5 of 5 gloved adjustments at B-22 | corrie_f_body.md 13.9, 13.5 |
| GT-1 | capstan pull: 5 kg on the guy over the packed bag's corner | release of this package | record MU_WEB_FAB (0.20-0.40 band) | corrie_f_body.md 13.9 |
| ALT-1 | alternate set: owner sees an ULTRAGrid swatch | release of this package | owner OK in writing | part A README section 1 |
| ALT-2 | alternate set: PT-3 on 200X + 50 mm strip test | release of this package | >= 36.8 N/mm (1840 N / 50 mm mean, FS-O5) | part A README; register FS-O5 |
| ALT-3 | alternate set: weigh the 70D stock | release of this package | gsm within +/- 5 % of nylon_ripstop_70d record | part A README |
| US-BS | US backstop: cam on 25 mm webbing with the stainless tri-glide threaded behind it; open the cam (forced slip) and load the strap to the US proof 1080 N (MT-1 basis, S5-S7 720 N x 1.5) | release of this package | tri-glide stops the strap within 10 mm and holds 1080 N for 1 min, 3 of 3 (ASSUMPTION US-BS) | triglide_25mm record note; DECISIONS 2026-11-13 |
| FRAY-1 | wash-swatch fray test of the un-bound SSa2 seam (3 wash cycles, R-12) | release of this package | no allowance frayed past the 2nd row; else bind (ASSUMPTION NO-BIND) | RD-17 |

## Defect list

| Defect | Where | Cause | Prevent / fix | Class |
|---|---|---|---|---|
| Skipped stitches in a box-X | load points | needle too small / wrong point, flagging on Hypalon | Nm 140 R, tex 135, walking foot pressure; re-sew the whole box offset 1 mm | critical |
| Box-X short (stitch count under the table) | load points | early stop, wrong program | count against the load table; re-sew | critical |
| Hardware threaded backwards (ladder lock, cam) | straps | assembly | QC-11 hand pull; SK-7 | critical |
| Load tab on the wrong face (B-17 out, B-18 / B-22 in) | B-01, B-02h | face mix-up | placement labels say INSIDE / OUTSIDE; check before sewing | critical |
| Needle-cut Hypalon / laminate (perforation line) | B-17, B-18, B-22, B-01 | cutting point needle or SPI too high | R point only; 8 SPI max on Hypalon | critical |
| Swell puckered or twisted in its window | B-01 | window not notch-matched | unpick, re-clip at the corners | major |
| B-27 port gapes (lap < 20 mm) | B-01 | facing sewn on the wrong line | re-sew on the drawn stitch line | major |
| Door zip waves / snakes at the corners | door | zip stretched while sewing | basting tape, corner notches, ease into the corner | major |
| Seam allowance frayed past the 2nd row | body seams | straight-knife cut nylon | laser / hot-knife cut or bind (FRAY-1) | major |
| Notch mismatch > 2 mm / seam end mismatch > 3 mm | box seams, collar ring | pieces stretched | re-clip notch to notch, walking foot | major |
| Mesh pocket over-stretched | FP | mesh pulled while sewing | baste the pleats first, sew with the mesh on top | minor |
| Thread tension loops on the underside | any | tension / bobbin | QC-06 swatch at each set-up | minor |
| Burn marks / hard beads on webbing ends | webbing | hot knife too hot / slow | J8 stop, steady cut | minor |
| Camo piece cut against the print direction | B-02u, SH-* | lay error | ONE WAY lay rule | minor |
| Hook-and-loop or a non-coil zip fitted | any | substitution | BOM check (owner: quiet bag) | critical |
