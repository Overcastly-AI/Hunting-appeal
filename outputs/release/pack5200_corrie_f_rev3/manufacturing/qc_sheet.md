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
| QC-13 | Final | Volume | fill with 10 mm foam balls / litre jug method, collar rolled 3 times | 85 L +/- 3 L (5200 cu in) (owner limit) | first article |
| QC-14 | Final | Mass, bag base | 1 g scale | within +/- 3 % of the ledger base bag (1065 g on the ledger basis; primary fabrics are heavier, see costing.md) | every bag |
| QC-15 | Final | No hook-and-loop, coil zips only | visual | zero hook-and-loop anywhere (owner: quiet bag) | 100 % |
| QC-16 | Final | Camo use | visual | camo only on B-02u, SH-07, SH-01b, FP-b, B-29f, A1-d (accents) | 100 % |
| QC-17 | Final | Thread ends, seals | visual | ends <= 3 mm, no open webbing ends, no burnt fabric | 100 % |
| QC-18 | Final | Labels | visual | ID label with rev 3 + date, size / crown kit, load-limit card (53 kg frame meat, RD-02) | 100 % |
| QC-19 | Final | Kits complete | count | base / as-hunted (lid, B-28 per kit, scope pod) / meat-trip (WX, B-24, liner) bags each complete | 100 % |
| QC-20 | Final | Fit on the frame | hook to a frame or the fit jig: hinge pins, IM eyes through B-12 ports, guys through B-27 | every eye reaches its port without strain; door opens fully | first article + 1 in 25 |

## Physical tests that gate release (no load point is sewn on a carrying bag before its test passes)

| ID | Test | Gates | Pass / fail | Source |
|---|---|---|---|---|
| MT-1 | 25 mm box-X bartack proof at the BL-010 per-row loads | every 25 mm box-X on IM1-IM3 and US1/US2 | 5 of 5 hold 908 N (IM) and 5 of 5 hold 1080 N (US) for 1 min, no broken stitch | test_register.csv |
| MT-2 | meat-strap hook proof per strap (BL-010) | IM free-end hooks | 5 of 5 G-hooks hold 645 N and 5 of 5 carabiners hold 910 N for 1 min, gates close | test_register.csv |
| MT-3 | 25 mm cam buckle slip at the BL-010 per-row loads | IM / US cams | mark moves < 3 mm at 908 N and at 1080 N, 5 of 5 | test_register.csv |
| PT-1 | IM3 bag carabiner on the sewn T3 tongue, per-row proof (BL-010) | IM3 carabiner on T3 | 5 of 5 hold 2553 N for 60 s, gate closes after, no visible set | test_register.csv |
| PT-2 | T3 tongue on the 70 mm B-17 tab on a B-01 swatch (BL-010 load) | T3 on the 70 mm B-17 tab | 5 of 5 hold 2553 N, no stitch break, no laminate tear | test_register.csv |
| PT-3 | HE eye on B-18 + B-01 + B-05 seam, built without binding | HE eye on B-18 (no binding) | 5 of 5 hold 1530 N | test_register.csv |
| PT-5 | guy ladder lock + tri-glide keeper slip | guy lock + tri-glide keeper | slip < 5 mm over 10 cycles | test_register.csv |
| PT-6 | B-24 float stand-off link | B-24 float link | 5 of 5 hold 1410 N, no box-X break, gate closes | test_register.csv |
| LL-H | heavy 25 mm ladder lock slip, 1 h hold (guys and W1-W3) | heavy 25 mm ladder lock slip: guys, W1-W3 and the B-28 crown straps (the B-28 slip gate since BL-031) | slip < 5 mm after 1 h, 5 of 5 (366 N covers the W 338 N proof) | test_register.csv |
| T9 | loaded CG (+ 15 in, 30 kg meat check; CORRIE F rev 3: port guys, crown strap cinch, lid) | rev 3 items: port guys at the S kit, crown strap cinch and free length, lid mass and seat | bag CG <= 205 mm at z <= 590; meat <= 190; tall <= 185; rev 3: CG <= 190 mm (record vs 181.3); cinch after the walk >= 40 N or the lid still seated on the full top (report the value); free length <= cut - 210 mm (1138 - 150 tail - 60 loop = 928 mm); lid 45.9 g +/- 5 g (record); lid edge on the hinge-band seam, caps over the blades | test_register.csv |
| FS-O5 | ULTRA 200X 50 mm strip tensile (C-5 / O-5) | alternate fabric gate: ULTRA 200X 50 mm strip (floor / frame side) | mean >= 1840 N/50 mm, minimum >= 1195 N/50 mm | test_register.csv |
| B-28 slip | B-28 crown strap on its heavy ladder lock: covered by LL-H at 366 N (BL-031 dropped the 20 mm gate; 25 mm strap on ladder_lock_25mm_heavy) | release of this package | LL-H pass | corrie_f_body.md 15.6 / 16 |
| PORT-1 | B-27 port mock-up: hose from above 1 min with the guy pulled at 45 deg; 100 N guy pull through the lap; gloved lock use at the port | release of this package | no water inside; lap stays closed at 100 N | corrie_f_body.md 13.9 |
| GT-1 | capstan pull: 5 kg on the guy over the packed bag's corner | release of this package | record MU_WEB_FAB (0.20-0.40 band) | corrie_f_body.md 13.9 |
| ALT-1 | alternate set: owner sees an ULTRAGrid swatch | release of this package | owner OK in writing | part A README section 1 |
| ALT-2 | alternate set: PT-3 on 200X + 50 mm strip test | release of this package | >= 36.8 N/mm (1840 N / 50 mm mean, FS-O5) | part A README; register FS-O5 |
| ALT-3 | alternate set: weigh the 70D stock | release of this package | gsm within +/- 5 % of nylon_ripstop_70d record | part A README |
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
