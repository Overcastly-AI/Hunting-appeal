# BL-037 Weight push: the last 220 g

**Agent:** pack-designer (lead; it may ask the structural-fea-engineer for checks via its report) · **Size:** L · **Depends on:** BL-036

## Where we are
Pack (CORRIE F rev 3 on H1, belt M, base): 3679.4 g proven now, 3211.4 g after tests. The target is 6.6 lb (2993.7 g), so it is **218 g away after tests**. BL-008 found the gap to the leaders is on the frame side: frame, back system, belt, harness and meat straps.

## Tasks
1. **Lever list:** from `huntkit/mass/ledger.py` and `weight_rollup_v2`, rank every system by mass against the cited leader figures (`docs/research/published_weight_definitions.md` and the other research docs). Find where we are heaviest per function.
2. **Candidates:** list every candidate lever with grams, risk, test gate, effect on the owner rules (fixed decisions in DECISIONS.md: adjustable torso with three crown kits, no wings, no hood, the rev 3 top, 25 mm crown straps, aluminium cams), and effect on build hours. Include the open items already found:
   - spreader load-share (about 22 g);
   - 28 mm cheek booking;
   - CA-1 at 0.40 (the −70 g lever);
   - harness and belt foam/fabric;
   - frame print parameters;
   - stays;
   - lighter primary fabrics.
   Owner-rule changes may be listed as options but not adopted.
3. **Pick a set** reaching ≥ 220 g after tests with the lowest risk. Keep every rev C safety factor (HA-LS-1). Each pick needs its check: run the existing huntkit checks (FEA, fatigue, loadpath) where a structural part changes; anything that can't be checked on paper gets a physical test gate in TEST_PLAN.md.
4. **Implement the low-risk picks** in code and ledger, regenerate the roll-up and the release folders, and run the full suite. Higher-risk picks go to the owner as options with numbers.
5. **Screenshots:** a before/after waterfall and a lever table. Prefix `20261113_BL037_`.
