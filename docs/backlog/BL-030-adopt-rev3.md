# BL-030 Adopt CORRIE F rev 3 as the design of record

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-029 (owner adopted rev 3 on 2026-11-12)

## Tasks
1. **Default:** make rev 3 the module default in `designs/pack_5200/concepts/corrie_f.py`, keeping revs 0–2 reproducible. Update the ledger configs (`huntkit/mass/ledger.py`) so the adopted configuration is rev 3: crown lid and crown straps in, top pouch out. Update `weight_rollup_v2` and the weight statement.
2. **Crown strap diet:** size the B-28 cut from the rolled 6-day top path (about 505 mm) plus adjustment range over the full 15–23 in and fill range. Try 20 mm webbing against hardware ratings and the 96 N (288 N factored) guy and lid loads. Target −15 to −25 g. Re-check the lid's hold with a 1 g and 3 g drop case on paper.
3. **Viz:** update `huntkit/viz3d/corrie_f.py` so it draws rev 3 natively (port guys hidden inside, crown lid and straps, no pouch, no outside guys), retiring the run-time swap in `corrie_f_rev3_viz3d.py`. Fix the lid close-up framing (bag sitting low with empty space above).
4. **Records:** add a §13 note in `corrie_f_body.md` that BL-028's "wrap" and "tie_wrap" eyelets were reversed (corrected rev 1 = 198.1 mm, still fails). Add rev 3 rows to `docs/release_delta_register.md/.csv`. Add physical test T9 (port guy at S kit, top full; crown strap cinch force with spring scale; sewn lid photo and weigh) to `designs/pack_5200/tests_physical/TEST_PLAN.md` and `test_register.csv` if missing.
5. **Lid build hours:** ask for a pattern-maker style check of the 7.8 h estimate from the lid's seam list; record the result.
6. Run the full test suite. Render hero, side, lid close-up and lid open with the updated viz, prefix `20261112_BL030_`; copy the best four to docs/screens.

## Acceptance
Rev 3 is the default everywhere (code, ledger, roll-up, renders); full suite passes; crown straps lighter with ratings shown.
