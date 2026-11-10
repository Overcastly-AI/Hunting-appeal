# BL-006 Hipbelt B diet

**Wave:** 1 · **Agent:** pack-designer · **Size:** M · **Depends on:** BL-001

## Why
Hipbelt B with its load path, pad seat, pockets and holster weighs 559 g at belt M. The Stone Glacier 3-piece belt is 363 g. The heaviest lines: 50 mm webbing, buckle, stabilizers and ladder locks 92 g; centre plate 78 g; HDPE wing stiffeners 41 g; bottle holster 39 g; wing load foam 30 g; pad seat about 61 g.

## Goal
Keep belt B's pressure and slip results; reach **≤ 490 g** at belt M in base configuration (stretch 470 g).

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/hipbelt_fit.md`, `hipbelt_structural.md`, `weight_c_structural.md` (C-1 to C-4 verdicts; the 7075 plate package and the CFRP pad backer are already adopted); `huntkit/gendesign/hipbelt.py`, `hipbelt_structure.py`; `designs/pack_5200/concepts/hipbelt_concepts.py`; `corrie.py` (`belt_b`, `hip_layout`, `holster`, `pad_seat`).

## Tasks
1. Tabulate belt B part by part from the ledger with each part's job and, for load-path parts, the margin on file.
2. Evaluate with the existing pressure model (16 ANSUR hip forms) and structural checks:
   - **(a)** front closure: 50 mm webbing and buckle → 38 mm with the 2:1 pull (check buckle rating, tension 483 N worst case, and comfort of a narrower front strap);
   - **(b)** stabilizer straps: are both needed with the fixed wing joint?
   - **(c)** wing stiffener: HDPE 1.0 mm full length → shorter or perforated, keeping the tip-to-hip-bone clearance result;
   - **(d)** foam: thickness and density map against the pressure result;
   - **(e)** bottle holster as an add-on outside base weight (it clips on with G-hooks already);
   - **(f)** pad-seat parts.
3. For each change: grams, wing peak pressure (median and worst), lumbar peak, hold ratio, and any structural margin that moves. Reject any change that makes worst-case wing peak pressure exceed belt B's 56.5 kPa or the hold ratio fall below 0.64.
4. Recommend a package. List load-path changes for BL-010.

## Deliverables
- `designs/pack_5200/concepts/hipbelt_diet.py`, `tests/test_hipbelt_diet.py`
- `designs/pack_5200/analysis/hipbelt_diet.md`
- `outputs/screens/20261111_BL006_1.png` (grams saved vs pressure change per item)

## Acceptance
- Belt B's published numbers (worst wing peak 56.5 kPa, hold 0.72 median / 0.64 worst) are reproduced first.
- The package states base-configuration and as-hunted mass separately.

## Out of scope
Editing `hipbelt.py` or `hipbelt_structure.py`. Changing the five sizes or the cone angles.
