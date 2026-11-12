# BL-024 H1 body: sleeve and crown-leg seat redesign for fatigue margin on the sim loads

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-021, BL-025 (corrected contact forces)

## Why
On CORRIE F's cloth-sim loads the H1 printed body's fatigue margin is **1.001** (23 in, meat case, left stay sleeve wall at the crown bore). On the beam loads it is 1.150. Adding wall outside the sleeve barely helps: +191 g only reaches 1.131. The H1 frame release R1 is held until this has margin. See `designs/pack_5200/analysis/im3_body_simloads.md` (BL-021).

## Goal
H1 body fatigue **≥ 1.15** on the sim loads at every torso and crown kit (S/M/L), with strength ≥ 1.4, at the least added mass, buildable on the H2S.

## Tasks
1. Reproduce BL-021's 1.001 and its location first.
2. Explore bore-side and load-path changes, for example:
   - a longer crown-leg engagement or a second bushing that spreads the leg moment;
   - a bonded or bolted sleeve liner (carbon or aluminium tube) inside the bore;
   - a local orientation-aware wall shape;
   - moving the governing hot spot by changing where the bushing bears;
   - crown kit leg lengths that keep more leg in the stay at the top setting.
   Keep every interface (crown kits per DECISIONS 2026-11-11, pawl/rack, IM3 28 mm cheek, spreader clips, back rails, pad seat).
3. Re-run all rev C sets on the beam loads and on the sim loads (use BL-025's corrected contact forces if they have landed; otherwise state the basis). Report per torso and per crown kit.
4. Update the H1 print files only if the result passes; otherwise propose. Give mass, print time and build steps.
5. Restate the CA-1 flip point for the final body.

## Deliverables
`huntkit/gendesign/h1_sleeve.py`, `tests/test_h1_sleeve.py`, `designs/pack_5200/analysis/h1_sleeve.md` (+ json), screenshots `outputs/screens/20261112_BL024_*.png`.
