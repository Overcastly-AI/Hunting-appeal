# BL-015 Release delta register

**Wave:** 1 (independent, low CPU) · **Agent:** manufacturing-engineer · **Size:** M · **Depends on:** none

## Why
The released v3.1 package no longer matches the design, and the corrections are scattered across analysis documents. The old frame print folder already carries a DO NOT PRINT notice. Before any release, someone needs one list.

## Goal
A single register of every difference between the released files and the current decisions, so a later release ticket can work through it.

## Read first
`docs/backlog/RULES.md`; `docs/DECISIONS.md` (every row from 2026-11-05 on); `docs/RESUME.md`; `outputs/release/pack5200_v3.1_patterns/README.md` and `cutlist.md`; `designs/pack_5200/print/frame/PRODUCTION.md` and `README.md`; `designs/pack_5200/analysis/frame_h1.md` §7; `weight_c_structural.md`; `hipbelt_structural.md`; `meat_carry_alternatives.md`; `bag_attachment.md`; `designs/pack_5200/cut/`.

## Tasks
1. Build the register: one row per delta with `id, area (frame / back / belt / harness / bag / attachment / meat haul / docs), released state, decided state, decision date and source, files that must change, blocked by (test or owner decision), safety-relevant (yes/no)`.
2. Known items to include at least: orange flag sleeve F-03 removed; swing mode replaced by float with B-24 links; H1 frame replaces the printed body and the flat print halves mismatch; P-1 crown socket bondline; lumbar backer CFRP 0.8 mm; yoke plate 1.8 mm; 7075 belt plate package; hipbelt B replaces the released belt; 4 × M5 pivot mount; attachment parts B-17 to B-24; back rails 120 mm with BP-08 backers; z 234 dowel booking; corrected material records.
3. Mark which released files are unsafe to build from today, and check each carries a visible warning. List any that do not (do not edit them; report).
4. Propose a release order.

## Deliverables
- `docs/release_delta_register.md` and `docs/release_delta_register.csv`

## Acceptance
- Every row cites its decision source. No row says "see analysis" without a file and section.
