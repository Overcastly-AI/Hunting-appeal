# Bag design competition (owner request 2026-11-10)

Owner: "I also would like to see a design competition of designing the bag. Must be good blender representations."

## Goal
The best main bag system for the 5200 pack on the H1 printed frame: main bag, pockets, lid or pouch, and wings or compression.
- **Baseline to beat:** CORRIE B.2 (designs/pack_5200/concepts/corrie.py, analysis/corrie_body.md §11–12). That is 3964.5 g at belt M with today's frame, ~3943 g with H1.
- **Teams may evolve CORRIE or replace it.**

## Fixed (every entry keeps these)
- **Frame interface:** hood B-19 over the crown top bar, B-20 ladder, B-22 guys, IM2/IM3 rated hooks with B-17/B-23, hinge pins with B-18, B-24 float links, under-straps US1/US2, internal meat straps IM1–IM3, fairleads, the bow riser carry, the rain fly in a base pocket.
- **Volume and size:** main bag 85 L ±3 (5200 cu in) to the fill line, width ≤ 15.5 in (394 mm), depth ≤ 12 in.
- **Owner look and sound:** mostly solid colours with the owner's camo (huntkit/camo; the viz3d camo texture) as edgy accent panels. Quiet: no hook-and-loop on the bag, coil zips.
- **Loads:** HA-LS-1 rev C bag-load CG basis (designs/pack_5200/analysis/load_standard.md). The bag-fill CG must be ≤ 205 mm and the meat CG ≤ 190 mm at 15/19/23 in torso, shown by cloth sim (huntkit/clothsim) or a defended estimate.
- **Access:** the hourly items in designs/pack_5200/loadouts.yaml (phone, water, snacks, inReach, spotter/tripod at glassing) must be reachable pack-on. Re-run the loadout check (designs/pack_5200/concepts/corrie_loadout.py as the pattern).
- **Patent guardrails and IP:** see docs/DECISIONS.md. Original IP only; never copy a brand's look.
- **Build:** buildable by a beginner on one walking-foot machine, with mostly straight seams.

## Rules
1. **Research first, cited:** each team writes docs/research/bag_comp_<team>.md, with a URL on every claim (it may reuse docs/research/bag_body_architectures.md and hunting_loadouts.md).
2. **Code and files:** code goes only in designs/pack_5200/bag_comp/<team>/ (python modules and data). Results go in designs/pack_5200/analysis/bag_comp_<team>.md, tests in tests/test_bag_comp_<team>.py and screens in outputs/screens/20261110_bag<team>_<n>.png (≤1.5 MB). Do NOT edit shared modules (huntkit/*), CORRIE files, docs/DECISIONS.md, released files or other teams' files. A new clothsim pattern loader goes in your team folder and imports huntkit.clothsim (see huntkit/clothsim/corrie_bag.py for how CORRIE did it). Do not commit.
3. **Renders, the owner's hard requirement:** Blender Cycles via huntkit/viz3d/cycles_render.py. The venv is at /tmp/claude-0/-home-user-Hunting-appeal/4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/scratchpad/bpyenv/bin/python; reinstall per huntkit/viz3d/README.md if it is missing. **The quality bar is at least outputs/screens/20261109_corrie_b2_1.png and _3.png:**
   - a draped fabric shape (cloth sim, or Blender's own cloth/softbody, not rigid boxes);
   - the real owner camo texture at true scale;
   - fabric sheen and ripstop bump;
   - real-looking zips, webbing and buckles;
   - shown on the display form with the frame and harness.
   Required shots:
   - (1) hero 3/4 rear;
   - (2) side profile;
   - (3) access, i.e. the bag open showing how you get in;
   - (4) a feature close-up (the team's best idea);
   - (5) a meat-haul view.
   Use 1600×1200 at ≤ 64 samples. **Look at every image yourself and iterate until it looks like product photography.** No placeholder blocks, floating parts, z-fighting or pixel camo. A crude render loses the look score however good the engineering is.
4. **CPU is shared (4 cores, 6 agents):** use coarse cloth meshes for the CG checks and one fine drape for the renders; run only your own tests; no full suite.
5. **Results file:** write designs/pack_5200/bag_comp/<team>/result.json with these keys:
   ```
   team, name, one_line, bag_system_g (bag + pockets + lid/pouch + wings/compression + fly, belt-independent),
   pack_mass_M_g (on H1: 3943 - corrie_b2_bag_system_g + bag_system_g; state the CORRIE number you used),
   volume_L, fill_height_in, pieces, curved_seams, zip_mm_total, beginner_hours,
   cg_fill_mm {"15","19","23"}, cg_meat_mm {"15","19","23"}, cg_method ("clothsim"|"estimate"),
   access_misses {"day","elk6","sheep8"}, features (list), risks (list), screenshots (list)
   ```
6. **Honesty:** state the weaknesses. A truthful entry beats a flattering one.

## Judging
An independent design-reviewer judges the entries; the owner makes the final pick from the renders.
- **Gate:** the fixed list, plus renders that meet the bar.
- **Score:** function and access 25 %, render quality and look 20 %, weight 20 %, build simplicity 20 %, carry/CG 15 %.

## Teams
- A **EVOLVE**: the best possible CORRIE: refine its shape, door, wings, pouch and pockets; fix its known weak spots (snacks on S–L belts, sheep-load poles, boxy look).
- B **LEAN**: the lightest bag that still meets the fixed list: roll-top first, minimal zips, modular add-on pockets.
- C **OPEN**: full-access hauler: clamshell or panel-loader with the whole back face opening, built for fast camp, kill-site and meat work.
- D **MODULE**: a modular system: a harness or shell on the frame carrying removable dry-bag or compartment modules, with meat swapping into a module.
- E **FORM**: a styling-led concept: a sculpted original silhouette and bold use of the owner's camo, while meeting every functional rule.
