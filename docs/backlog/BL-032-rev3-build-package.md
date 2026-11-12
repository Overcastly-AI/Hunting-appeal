# BL-032 CORRIE F rev 3 cut and sew package

**Agents:** pattern-maker (part A), then manufacturing-engineer (part B) · **Size:** XL · **Depends on:** BL-031

**Fabric:** today's fabrics are the primary BOM. The team B set is an alternate column (see DECISIONS 2026-11-12).

## Part A: patterns (pattern-maker)
1. **Every sewn piece of the rev 3 bag:**
   - S15 shell with door D2;
   - collar and roll top;
   - hip-reach pockets;
   - B-27 port slits and B-22 hinge band anchors;
   - B-29 crown lid;
   - the strap and keeper pieces from BL-031;
   - the meat-trip kit extenders.

   Take geometry from `designs/pack_5200/concepts/corrie_f.py` (rev 3 is the default) and `corrie_f_body.md` §12–16. Mark the seam allowance, notches, drill holes, grain and piece IDs on each piece.
2. **True-scale exports:**
   - DXF (AAMA);
   - tiled PDF cut sheets with a scale check square;
   - nested cutting markers per fabric, with utilization.
3. **Lid build-hours check:** check the B-29 lid hours (BL-030 seam-list estimate 8.94 h, booked 7.76 h) on the drafted pattern.
4. **Release location:** `outputs/release/pack5200_corrie_f_rev3/patterns/`, with a README. The v3.1 patterns stay superseded; keep their STOP notice.
5. **Screenshots:** piece layout and a marker.

## Part B: manufacturing (manufacturing-engineer, after A)
1. **BOM:** primary and alternate fabric columns, with hardware and thread. Every line traces to a `data/materials/` record or an ASSUMPTION.
2. **Sewing operation sequence:** a beginner-readable order, with ISO 4915/4916 stitch and seam specs, bartack specs at load points (port guys, crown straps, IM3, W1–W3), and jigs.
3. **QC sheet:** points and tolerances, plus the physical tests that gate release (T9 items, B-28 slip, fabric gates for the alternate set).
4. **Costing and hours.**
5. **Tech pack PDF:** in the same release folder, with a rasterized preview.
6. **Delta register:** close or restate the RD rows this release resolves.

## Acceptance
- The piece list reconciles 1:1 with the ledger's bag rows.
- Mass from the pattern areas is within ±3 % of the ledger.
- Tests pass.
