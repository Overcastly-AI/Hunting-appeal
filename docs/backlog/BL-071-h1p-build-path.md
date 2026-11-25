# BL-071 H1-P (PPA-CF) build path: coupons first, H2S print sheet, through-bolt hip, BOM

**Agent:** manufacturing-engineer · **Size:** M · **Depends on:** BL-070 (`bl070_h1p.json`), BL-072 (review 8) · **Date:** 2026-11-25

Ask: add a PPA-CF H1-P build path alongside the PAHT-CF H1 path (which stays the fallback): register rows and test-kit
sheets for CA-1/3/4-PPA and T4c-PPA with the BL-070 pass lines (read from the JSON), HB-6-PPA marked not needed, a
coupon print plan of about one spool with the gate, an H2S print sheet with sourced values, the 8 x Ti M5 x 20 through-bolt
hip mount, and the PPA BOM / cost.

Mid-task (orchestrator): review 8 (`designs/pack_5200/analysis/review_20261125_eighth.md`) put H1-P on HOLD. The print
sheet and the frame build steps are marked "HOLD — not released (review 8 B-1/B-2)"; coupon prints stay allowed. No
hip torque is set (TBD by BL-073). The review's coupon findings are written up, not fixed (BL-073 owns the pass lines).

## Deliverables
- Code: `designs/pack_5200/frame_h1p_build.py` (new). Reads `bl070_h1p.json`, `ppa_cf_fdm.yaml`, review 8's summary table
  at generation time; writes the docs, the T4c stay STL, the BOM / coupon CSVs, PDFs, tech pack (`huntkit.manufacturing.techpack`).
- Wiring: `designs/pack_5200/physical_test_kit.py`: register rows from `frame_h1p_build.register_rows()`, release
  `R1-PPA`, session `G8`, results rows, beginner steps, 4 shopping lines (rig extras; spools and dryer stay on the
  BUILD_H1P BOM). `frame_h1_build.py`: a pointer from the H1 README to the PPA path.
- Docs (generated): `designs/pack_5200/print/frame_h1p/{README,COUPONS_H1P,PRINT_SHEET_H2S,BUILD_H1P}.md`,
  `test_pieces/t4c_stay_R.stl` (+ `_frame_coords.stl`).
- Release: `outputs/release/frame_h1p_ppa/` and `outputs/release/test_kit/` (G8 guide, register-driven files).
- Tests: `tests/test_bl071_h1p_build.py`.

## Result
- Pass lines (from the JSON text, cross-checked against the numeric fields within 0.5 %): CA-3-PPA conditioned Z
  >= 31.3 MPa and SBS >= 18.8 MPa (mean - 2.4 SD); CA-1-PPA all 12 run out at 0.279 x UTS; CA-4-PPA 0.85 / 0.75 / 152 MPa;
  T4c-PPA -20 C, 1.22 m. All under review (M-3, M-4, M-8; B-2).
- Coupons (jobs A + B): 471 g = 0.63 spool; spool 1's rest (279 g) covers both halves' run-out swaps (101 g).
- **Filament: 3 spools, $449.97, covers the frame and the gate coupons only. The T4c-PPA stays (3 x 212 g + supports =
  832 g) need a 4th spool ($149.99) plus 82 g of spool 1.** Dryer: no consumer dryer reaches 120 C (SUNLU E2 110 C);
  a benchtop forced-air oven, ASSUMPTION $376.90 (search snapshot).
- Hip: 8 x Ti gr5 M5 x 20 DIN 7984 + A2 DIN 934 nuts + Loctite 243; stack 3 + 13 + 4 = 20 mm (tip flush). Torque TBD.
  Insert install steps and HW-HIP-INS / -SCR / -GUIDE are gone from the PPA path.

## FOUND, NOT FIXED
- Nut face (= review 8 B-1): an 8 AF trap cannot take the D10 washer NUT-BEAR booked; on the nut's dw 6.9 ring (13.6 mm2)
  the same rule reads fatigue 1.06 (goal 1.15). A creep-capped preload on that ring gives only ~0.16 N m (information for BL-073).
- The conditioned XY static pulls of CA-1-PPA (~4.9 kN at the bar) overrun the kit B 100 kg cell and put ~300 MPa in the
  single 40 x 10 6061 lever: a 200 kg cell and a doubled lever are on the shopping list (ASSUMPTION LEVER-XY).
- T4c-PPA's 3 PPA stays do not fit the "about one spool" coupon budget; BL-070's "3 spools, about $450" omits them.
- T4c-PPA's bend load (1.5 x C4 set-down stay moment) is not in `bl070_h1p.json`: PENDING structural.
- Home freezers hold about -18 C; the -20 C soak needs a chest freezer (ASSUMPTION FREEZER, recorded per run).
- The kit PDF passed 99 pages, so pdftoppm writes 3-digit preview names; the kit now clears stale previews.
