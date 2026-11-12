# BL-029 Top anchor and lid redesign, informed by Exo and peers

**Agent:** pack-designer · **Size:** L · **Depends on:** BL-028

## Why
- **Owner (2026-11-12):** "Look at the exo bags. Our pouch does not look right on this bag."
- **BL-028:** CORRIE F rev 1's guys fail rev C as built. On their real outside path the 15 in meat CG is 194.9 mm against the 190 limit. Rev 2's fix runs the guys inside the bag (181.9 mm), and the owner has not accepted it; they pointed at Exo instead.
- **The pouch:** CORRIE F's 2.7 L top pouch is a box strapped on the roll. It does not look like part of the bag (BL-020, BL-026 renders).

## Goal
A top anchor and lid/pouch that look like one designed system, hold the bag top to the frame so the **15 in meat CG ≤ 185 mm on the fine mesh** (rev C 190), keep R-28 ≥ 31° and keep the lifters on the crown top bar (patent guardrail). Original IP only.

## Tasks
1. **Research, cited** (`docs/research/top_anchor_and_lids.md`, URL on every claim):
   - **Exo Mountain Gear (K3/K4):** how the bag top attaches to the frame (compression straps over the frame top, load lifters, lid buckles); how their lid attaches, floats and is sized; what reviewers and owners like or dislike.
   - **Peers, same questions:** Stone Glacier, Kifaru, Seek Outside, Mystery Ranch.
   - **Patents:** check any relevant to top straps or lids.
   - **Look:** describe the visual language that makes a lid read as part of the bag (shape following the roll or crown, shared seam lines, colour blocking). Never copy any brand's look.
2. **Concepts.** Propose 2–3 integrated top systems. Candidates:
   - a floating lid that also serves as the top anchor (its rear straps go to the frame crown, its front straps to the bag's aft face, so it pulls the bag top forward over the roll);
   - over-the-top compression straps from the crown to the bag's aft face that pass over the roll and hold the lid;
   - rev 2's inside guys with a lid redesigned around them.
   For each: the look (sketch and quick render), mass via `huntkit/mass/ledger.py` systems, gloved access steps, and the patent check.
3. **Simulate** the best one or two on the fine cloth mesh with the real strap paths (BL-028's `--route` machinery, straps wrapping the roll; no straight lines through cloth): 15 / 19 / 23 in meat and fill CG, R-28, IM3 and guy loads, lifter clearance at every crown kit.
4. **Recommend one.** Put it in `designs/pack_5200/concepts/corrie_f.py` as rev 3 (keep revs 0–2 reproducible), and update `corrie_f_body.md` (§14) and the tests.
5. **Render** it through the studio layer (`huntkit/viz3d/`, cloth pass): hero on the 6 ft hunter at a 6-day load, side, a lid close-up, and a lid-open view. They have to look like one bag. Prefix `20261112_BL029_`; copy the best four to docs/screens.

## Acceptance
- 15 in meat CG ≤ 185 mm (fine mesh, real strap paths); R-28 ≥ 31°; lifter gap ≥ 10 mm at every kit.
- The lid reads as part of the bag in the renders.
