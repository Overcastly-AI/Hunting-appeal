# BL-017 Crown and torso-adjust block: lighter while staying adjustable

**Wave:** 2 · **Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-007 (read its findings first)

## Why
If the owner keeps the adjustable torso (BL-007 is an owner decision), the fixed block of crown legs, top bar, spine tube, corner wraps, rack, pawl, guides and bushings (about 250 g with the torso adjust) is still the largest untouched part of the frame. The crown legs are at margin 1.12, so thinning is not an option; architecture is.

## Goal
Options that keep torso adjustment and the top bar and save **≥ 60 g** on this block.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/frame.yaml` (crown, `crown_rev_b`); `designs/pack_5200/print/frame/PRODUCTION.md` (carbon crown section); `rev_c_verification.md`; `frame_cg_recheck.md`; `frame_h1.md`; BL-007's `frame_fixed_torso.md`.

## Tasks
1. Break the block down part by part with mass and governing margin.
2. Evaluate at least:
   - **(a)** shorter adjust range (for example three sizes of frame, each with ±40 mm, instead of one frame covering 15–23 in), which shortens the legs and the sleeves;
   - **(b)** pinned positions instead of rack and pawl;
   - **(c)** larger-diameter thinner-wall legs at the same stiffness;
   - **(d)** the 3:1 pulley adjust replaced by a simpler lock.
3. Re-run the crown checks for each (all rev C cases at the affected torso settings, including the hipbelt-off case that governs the legs and C6p for the post sockets).
4. Report mass, margins, parts, build steps, and the effect on hood ladder B-20 and the harness yoke.

## Deliverables
- `huntkit/gendesign/crown_diet.py`, `tests/test_crown_diet.py`
- `designs/pack_5200/analysis/crown_diet.md`
- `outputs/screens/20261111_BL017_1.png`

## Acceptance
- Today's crown margins (legs 1.12, top bar, spine) are reproduced first.
- No option is recommended below 1.0 on any check.
