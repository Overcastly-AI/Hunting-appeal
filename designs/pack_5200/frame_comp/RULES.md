# Printed-frame design competition (owner request 2026-11-10)

Owner: "I want a 3D printed option. I think it can be strong enough." and "Launch 5 agents as a design competition."

## Goal
The lightest 5200-pack frame made by **3D printing plus simple dry assembly** that passes **HA-LS-1 rev C** in full, fatigue included.
- **Allowed:** bolts, heat-set inserts, press/snap fits, bought pultruded rods or tubes captured mechanically, annealing.
- **Not allowed:** hand-wet carbon layup, wraps or moulds. The owner rejected TENDON for exactly that.

## Fixed interfaces (unchanged in every entry)
- **Crown and lifters:** the crown/top bar with the lifters (Mystery Ranch US 10,952,523 guardrail), the torso adjust (rack, pawl), and the P-1 crown socket bondline.
- **Bag hard points:** 8 fairleads, IM2/IM3 hooks, hinge pins, hood B-19 bar, B-22 guys, B-24 float eyes, under-strap pins US1/US2.
- **Hip and back:** the hipbelt B Ti pivot at z 120 with 4 × M5 inserts, the lumbar pad seat, and the Sandwich v2 spreader on its supports.
- **Patent guardrails:** see docs/DECISIONS.md.

## Baseline to beat
Today's production frame:
- PAHT-CF branch body 823 g; frame 1063 g; frame + spreader 1225 g.
- Worst margins: body fatigue 1.04, crown legs 1.12.

Sources: designs/pack_5200/print/frame/PRODUCTION.md, frame.yaml, analysis/rev_c_verification.md, analysis/weight_c_structural.md (C-9), analysis/frame_light2.md (TENDON; bond-to-printed-PA allowable 4 MPa hot/wet), designs/pack_5200/analysis/load_standard.md.

## Rules
1. **Research first, cited:** every team writes `docs/research/frame_comp_<team>.md`, with a URL on every material property. Use conservative published fatigue, interlayer (Z) and hot/wet data. Anything unpublished is an `ASSUMPTION` with a coupon test defined.
2. **Analysis:** use the repo tools (huntkit/fea, huntkit/gendesign); put new code ONLY in `huntkit/gendesign/frame_comp_<team>.py`. Never edit shared modules. Check every rev C case at torsos 15/19/23 in, with the bag couple on both the crown bar and IM3: strength, fatigue (1e5 cycles), creep, buckling, joint/bearing/insert.
3. **Files:** each team's files go only in `designs/pack_5200/frame_comp/<team>/`, `designs/pack_5200/analysis/frame_comp_<team>.md`, `tests/test_frame_comp_<team>.py` and `outputs/screens/20261110_comp<team>_<n>.png` (≤1.5 MB). Do not edit docs/DECISIONS.md, other teams' files or released files. Do not commit.
4. **CPU is shared (4 cores, 5 teams):** keep meshes modest, run only your own tests (not the full suite), and make at most 2 Blender Cycles renders at 1200×900 / 32 samples. Use the venv at /tmp/claude-0/-home-user-Hunting-appeal/4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/scratchpad/bpyenv/bin/python with huntkit/viz3d/cycles_render.py; reinstall per huntkit/viz3d/README.md if missing. Required images: your concept next to today's frame, and a utilization plot.
5. **Results file:** write `designs/pack_5200/frame_comp/<team>/result.json` with exactly these keys:
   ```
   team, concept_name, one_line, frame_g, frame_plus_spreader_g, pack_mass_corrie_b2_M_g,
   passes_rev_c (bool), worst_strength_margin, worst_fatigue_margin, worst_joint_margin,
   governing_case, torsion_stiffness_vs_today, print_hours, printer ("H2S home" | "service: <process>" | ...),
   cost_usd {"1":…, "10":…, "100":…}, build_hours, skill_level ("beginner"|"intermediate"|"expert"),
   looks_generative (bool), patents_checked (list), governing_assumptions (list), coupon_tests (list)
   ```
   CORRIE B.2 at belt M is 3964.5 g with today's frame, so pack mass = 3964.5 − (1225 − frame_plus_spreader_g).
6. **Honesty:** if your direction can't beat the baseline or can't pass rev C, say so with the numbers. A truthful failure scores better than an optimistic pass.

## Judging
A design-reviewer judges the entries against each other.
- **Gate:** passes rev C, with every governing assumption tied to a coupon test.
- **Score:** mass 40 %, build simplicity for a beginner owner 25 %, confidence/risk 15 %, cost 10 %, generative look 10 %.

## Teams
- A: **MONO**, today's monolithic body re-topologised for material, orientation and annealing (home H2S).
- B: **SEG**, segmented body, each segment printed along its own load path, bolted printed lap joints (home H2S).
- C: **ROD**, printed body with bought pultruded carbon rods/tubes captured in bolted printed clamshell channels, no adhesive in the load path (home H2S).
- D: **SERVICE**, service-printed MJF/SLS (PA12-CF, PA11-CF or similar) or other industrial process, free to re-topologise.
- E: **FIBRE**, continuous-fibre-reinforced printing (Markforged, Anisoprint, the Bambu/other CFC options), at home or by service.
