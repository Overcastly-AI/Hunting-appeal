# Backlog: lighter pack, better bag (created 2026-11-10)

Source: `designs/pack_5200/analysis/bag_weight_review_20261110.md`. Rules for every ticket: `RULES.md`.

**Starting point:** CORRIE B.2 on the H1 frame, belt M: 3927 g (8.66 lb). Leaders: 2308–2790 g.
**Main finding:** the excess is in straps and hardware (842 g) and suspension (2289 g), not bag fabric.

## Tickets

| ID | Title | Agent | Size | Depends on | Target |
|---|---|---|---|---|---|
| BL-001 | One mass ledger | pack-designer | M | — | one basis for every comparison |
| BL-002 | Close out the bag competition | design-reviewer | M | 001 | verified verdict + contact sheet |
| BL-003 | One strap architecture | pack-designer | L | 001 | −200 g (stretch −300 g) |
| BL-004 | Attachment diet | pack-designer | M | 001 | 303 → ≤ 220 g |
| BL-005 | Back system integration | structural-fea-engineer | L | 001 | 414 → ≤ 320 g |
| BL-006 | Hipbelt B diet | pack-designer | M | 001 | 559 → ≤ 490 g |
| BL-007 | Fixed-torso frame study | structural-fea-engineer | L | — | owner decision material |
| BL-008 | What the leaders count in published weights | pack-designer | S | — | base / as-hunted definitions |
| BL-009 | Bag shape sweep | pack-designer | L | — | 15 in meat CG ≤ 176 mm at 85 L |
| BL-010 | Verify changed load paths | structural-fea-engineer | M | 003, 004, 006 | pass/fail per load path |
| BL-011 | Merged bag "CORRIE F" | pack-designer | XL | 001, 002, 003, 004, 009, 010 | bag side −350 g |
| BL-012 | Blender renders of CORRIE F on H1 | pack-designer | L | 011 | product-photo quality |
| BL-013 | Weight roll-up v2 | pack-designer | M | 001, 005–008, 010, 011 | honest total, three scenarios |
| BL-014 | Independent review | design-reviewer | M | 010, 011, 013 | blockers found before the owner decides |
| BL-015 | Release delta register | manufacturing-engineer | M | — | one list of release changes |
| BL-016 | One physical test plan | manufacturing-engineer | M | — | ordered, costed test plan |
| BL-017 | Crown block diet (adjustable torso kept) | structural-fea-engineer | M | 007 | −60 g |

## Run order

The account hit its 5-hour usage limit twice with six agents running at once. Run **at most three agents at a time**.

| Wave | Tickets | Notes |
|---|---|---|
| 0 | BL-001 | alone; everything else reads the ledger |
| 1a | BL-003, BL-009, BL-007 | the three longest; BL-009 and BL-007 are CPU heavy, so start them first |
| 1b | BL-004, BL-005, BL-008 | start as 1a tickets finish |
| 1c | BL-006, BL-002, BL-015, BL-016 | BL-015 and BL-016 are documents only and can fill idle slots |
| 2 | BL-010, then BL-011; BL-017 beside them | BL-011 must not start before BL-010 reports |
| 3 | BL-012, BL-013 | |
| 4 | BL-014 | then the orchestrator takes the results to the owner |

## How to launch a ticket

Give the agent this prompt, with the ticket file name filled in:

> You are working one backlog ticket for the Hunting-appeal repo. Read `docs/backlog/RULES.md`, then `docs/backlog/<ticket file>`, and do exactly that ticket. Follow the report format in RULES.md. Do not commit.

After each ticket the orchestrator: reads the report, checks the listed tests were run, looks at the screenshots, commits, and adds a `docs/DECISIONS.md` row for engineering results. A ticket that reports "TARGET MET: no" is still complete if its numbers are sound.

## Owner decisions these tickets will tee up

Nothing here is decided; the tickets produce the material.

1. **Fixed-torso frame** (BL-007): give up torso adjustment for a lighter frame printed to size?
2. **Base weight definition** (BL-008): do the top pouch, bottle holster, scope pod, meat liner and float kit count in the published weight?
3. **Float parts as a meat-trip kit** and **no wings** (BL-003).
4. **Fabric swaps** (BL-011): visible-grid ULTRAGrid body, 70D collar, ULTRA 200X floor, each with its test gate.
5. **Door** (BL-011): full-face opening with load straps, or the camo-blade door.
6. **Published weight target** (BL-013): after the roll-up.

## Not in this backlog

- Physical tests themselves (the owner runs them; BL-016 plans them).
- The pattern release and manufacturing package for the new bag; they follow the owner's pick.
- The apparel line.
