# BL-014 Independent review of the wave 1–3 results

**Wave:** 4 · **Agent:** design-reviewer · **Size:** M · **Depends on:** BL-010, BL-011, BL-013

## Goal
Find what is wrong before the owner decides. Review the files, not the summaries.

## Read
`docs/backlog/RULES.md`; the deliverables of BL-003 to BL-013; `designs/pack_5200/analysis/load_standard.md`; `docs/DECISIONS.md`.

## Tasks
1. **Re-run:** run every new test file. Re-run one headline number per ticket yourself (for example the BL-009 chosen shell's 15 in sim, one BL-010 margin, the BL-013 total).
2. **Hunt for:**
   - margins that rest on an assumption with no test defined;
   - double-counted savings (the same strap removed by BL-003 and again by BL-011);
   - functions lost in the strap consolidation (walk F1–F7 from BL-003);
   - patent-guardrail conflicts;
   - sewing steps a beginner cannot do on one walking-foot machine;
   - anything in a render that the design files do not contain.
3. **Check the claims:** each ticket's "TARGET MET" against its own numbers.
4. **Rank:** findings as blocker, should-fix or note, each with the file and line or the number.

## Deliverables
- `designs/pack_5200/analysis/review_20261111.md`

## Acceptance
- Every blocker cites evidence you produced or a file location.
- You changed no design files.
