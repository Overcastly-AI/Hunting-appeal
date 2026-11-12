# BL-031 Crown straps sized per kit; no hanging tails anywhere

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-030

## Owner direction (2026-11-12)
- Crown straps stay **25 mm** (BL-029 spec; the 20 mm option is dropped).
- "Different sizes. We don't want straps hanging everywhere."

## Tasks
1. **Crown straps per kit:** make B-28 a sized part, with one cut each for the S, M and L crown kits (the torso range each kit covers is in the frame docs). Size each cut from the BL-030 path data (`corrie_f_crown_rolled.json`, `crown_strap_diet()`), using that kit's own torso range and the day / 6-day / full-with-collar-standing loads. Spread the remaining range between the shortest and longest path across the two adjusters. Report the worst-case free tail per kit.
2. **Tail target for every strap:** set one rule, e.g. a free tail of 100 mm (4 in) or less at the most-used setting (6-day load, mid torso), plus a tail management feature (elastic keeper, roll-and-velcro, or tuck channel) wherever the range forces longer tails. Then audit **every** adjustable strap on the pack against it, listing worst and typical tails:
   - shoulder and lifters;
   - sternum and hipbelt;
   - W1–W3;
   - IM straps;
   - B-24, B-25 and B-26;
   - roll-top;
   - the crown straps.
   Fix the offenders: change lengths, keepers or sizing. Book any mass change on the ledger.
3. **Code and records:**
   - Make 25 mm the default in `corrie_f.py` (`crown_straps(25.0)` per kit), keeping BL-030's 20 mm function only as history.
   - Update the ledger and roll-up, the release delta register (RD-24), and `corrie_f_body.md` (§16).
   - Drop the B-28 20 mm slip gate from §15.6.
   - Add a test.
4. **Renders:** re-render the hero and lid close-up at 25 mm, with tails at their real length and keepers drawn. Also render a close-up of the worst remaining tail area after the fixes. Prefix `20261112_BL031_`.

## Acceptance
Every adjustable strap meets the tail rule at the most-used setting or has a drawn keeper. Crown straps are 25 mm and sized per kit. The full test suite passes.
