# Bag competition, team D (MODULE): CACHE

Date 2026-11-10. Rules: `designs/pack_5200/bag_comp/RULES.md`. Research: `docs/research/bag_comp_D.md`.
Code (team folder only): `designs/pack_5200/bag_comp/D/` — `cache.py` (mass and build model), `clothsim_cache.py` +
`scenarios/` (cloth sim), `cache_loadout.py` (access), `module_cloth_bpy.py` (Blender cloth of the modules),
`cache_viz3d.py` (render model), `result.py` -> `result.json`. Tests: `tests/test_bag_comp_D.py` (7 pass).
CORRIE files, huntkit and released files are only imported and read.

## 0. The entry in one paragraph

A light shell carries removable modules. The shell is CORRIE rev B's proven frame-side shell: same B-01, gussets,
floor, fairlead swells and #10 horseshoe door, and the whole fixed interface. The wings, the roll-top hem, the HDPE
strips, the roll hardware and the top pouch are removed. A drawcord collar is cinched under a **LID module**. Inside
are three silpoly roll-top modules: the **SWAP slab** (frame zone, sleep kit), the **CAMP** module (aft, slides out
of the door like a drawer) and the **KILL** module (at the door sill). Outside, two hook-on parts use the old wing
loops: an **optics pod** (85 mm spotter) and a **tripod kit**.

Best idea: **the SWAP slab does two jobs.** In camp mode it is the sleep-kit module, cut to the IM1-IM3 strap zone, and
IM1-IM3 cinch it flat against the frame, so the meat straps are also the internal compression. On a pack-out you empty
it and put it back in at the frame as the wipeable meat liner. Boned meat goes in game bags inside it, with IM1-IM3
over it. The meat rides exactly where the rated straps hold it, the shell stays clean, and nothing extra is carried
for the job.

## 1. Lessons from CRADLE (bag_alternatives.md U.2-U.3), and what CACHE does instead

| CRADLE problem | CACHE |
|---|---|
| +161 g: an open harness *plus* four drybags in coated fabric | the harness is the shell itself (no double wall on the outside); modules in 45 gsm silpoly; only 3 modules ship |
| CG 168 mm aft: round drybags push the load out | flat box modules cut to the section; a 110 mm (4.3 in) slab at the frame; the cloth sim of the shell gives the same CG as CORRIE (section 4) |
| 45.5 in tall | 40.2 in fill height (CORRIE's) |
| open sides snag brush | closed 330D gussets; pods and the tripod kit sit outside them and come off |
| roll-top hardware dropped, drybag clips booked | roll + one G-hook keeper per module (no buckles, quiet), 6.7 g a module |

## 2. Mass (`cache.system()`; same metric as CORRIE: cut area x record gsm, records, stated ASSUMPTIONs)

DEFINITION (`cache.corrie_b2_system()`): **bag_system_g** = bag + pockets + lid/pouch + wings/compression + modules
+ pods + fly. It is independent of the belt and the harness, except that CACHE's own strap pocket SP is counted. The
fixed frame interface (hood, ladders, guys, hooks, tabs, IM straps and ports, under-straps, B-24, fairleads, bow riser
carry) is the same for every team and is left out on both sides. **CORRIE B.2 by this metric: 892.1 g** (body group
533.1, roll-top hardware 48.5, keeper loops 8.6, IMP-1 54.5, IMP-2 40.3, IMP-4 22.0, IMP-8 7.5, haul wraps 102.7, fly
74.9).

| Item | g | oz |
|---|---:|---:|
| Shell: CORRIE rev B body + door, no wings, drawcord collar D-07, 8 pod loops, 4 lid anchors, SH-09 camo bar | 379.4 | 13.4 |
| Haul-wrap keeper loops (kept) | 8.6 | 0.3 |
| IMP-2 hydration sleeve, IMP-8 cam cup (kept) | 47.8 | 1.7 |
| **MS SWAP slab** 330 x 110 x 560 mm (13.0 x 4.3 x 22.0 in), 20.3 L; silpoly tube, 70D frame face + floor | 61.7 | 2.2 |
| **MC CAMP** 250 x 160 x 430 mm, 17.2 L, silpoly | 39.1 | 1.4 |
| **MK KILL** 260 x 90 x 280 mm, 6.6 L, silpoly zip clamshell, #5 zip, 2 G-hook tabs | 36.4 | 1.3 |
| **ML LID** 280 x 190 x 60 mm, 2.7 L (CORRIE B.2 pouch box), 2 rear + 2 front cinch straps | 78.7 | 2.8 |
| **PO optics pod**: the IMP-1 sleeve as a free tube, 3 mm XLPE, 2 fixed tabs + 2 cinch straps, camo bar | 95.2 | 3.4 |
| **PT tripod kit**: foot cup + 2 cinch straps | 46.8 | 1.7 |
| **SP snack pocket**, right shoulder strap (fixes the S-L snacks miss) | 19.7 | 0.7 |
| Haul wraps W1-W3 (compression; also carry float mode) | 102.7 | 3.6 |
| Rain fly F-01 (CORRIE B.2 box re-cut) | 74.9 | 2.6 |
| **bag_system_g** | **991.0** | **35.0** |
| vs CORRIE B.2 892.1 g | **+98.9** | +3.5 |
| **pack_mass_M_g** on H1 = 3943 - 892.1 + 991.0 | **4041.9** | 8.91 lb |
| Without the three in-bag modules (MS + MC + MK = 137.2 g) | 853.8 | -38.3 vs CORRIE |

Honest reading. Counted strictly, CACHE is **99 g heavier than CORRIE B.2**. That beats CRADLE's +161 g but loses the
weight criterion. The shell system without modules is 38 g *lighter* than CORRIE. The three modules weigh about what
the stuff sacks they replace weigh (a 20 L Ultra-Sil dry sack is 50-58 g, research section 3). So the hunter's
*carried* weight is about even only if they really leave their stuff sacks at home.

Mass ASSUMPTIONs: G-hook 4 g and #8 slider 4 g (as CORRIE); #5 slider 2.5 g; drawcord channel 40 mm folded;
cord 1.45 m; module roll keeper = 0.15 m webbing + G-hook; HDPE roll strip 20 mm wide on two faces of each roll-top
module.

## 3. Volume and size

- Main bag: the CORRIE rev B shell to the same fill line (collar seam z 736.3, fill line z 1056.1): **85.2 L design
  basis** (R-01, as CORRIE). The cloth sim gives a closed volume of **87.1-88.4 L (5316-5395 cu in) loaded**, mean
  87.9 L. Width 393.6 mm (15.5 in); max depth 258 mm (10.2 in) flat-panel, under 12 in. Fill height **40.2 in**.
- The modules hold 20.3 + 17.2 + 6.6 = 44.1 L *inside* that volume. The rest is loose (bladder sleeve, layers on
  top, food overflow). The module walls and corners cost usable volume: ASSUMPTION fill efficiency 0.90 -> 0.86, used
  in the loadout check. The LID (2.7 L) and the pods ride outside and are not counted in the 85 L.

## 4. Carry / CG: cloth sim (`huntkit.clothsim` through `clothsim_cache.py`)

The shell pieces are CORRIE's, so the pattern loader is CORRIE's loader, relabelled. The base scenarios are the
converged `corrie_PR{15,19,23}c` settings: 6 mm contact rounding, then continuation to 0. The changes are the
external loads. The LID module (1.0 kg + 79 g) sits on the cinched closure, 40 mm above it. The optics pod
(1910 g spotter + 75 g pod) hangs on the same 4 loops CORRIE's left wing used, split 50 / 50 (ASSUMPTION, as
CORRIE). Coarse mesh, h 40 mm (RULES section 4). Runs: `outputs/clothsim/bagD_cache_PR{15,19,23}/results.json`.

| Torso | Case | Converged (rounding) | Residual N | Closed L | **CG y incl. lid + pod, mm** (limit, margin) | CG z | Worst seam (SF) |
|---|---|---|---:|---:|---|---:|---|
| 15 in | fill | yes (6 mm) | 0.49 | 88.2 | **191.4** (205, 13.6) | 496 | B-03L/B-05 1.43 N/mm (14.3) |
| 15 in | meat | yes (6 mm) | 0.26 | 88.4 | **182.1** (190, **7.9**) | 507 | B-03L/B-05 1.75 (11.7) |
| 19 in | fill | yes (4 mm) | 0.32 | 88.4 | **174.1** (205, 30.9) | 507 | 1.29 (15.9) |
| 19 in | meat | yes (3 mm) | 0.46 | 88.1 | **167.2** (190, 22.8) | 515 | 1.61 (12.7) |
| 23 in | fill | yes (6 mm) | 0.30 | 87.1 | **131.4** (205, 73.6) | 516 | 1.11 (18.5) |
| 23 in | meat | yes (0 mm) | 0.12 | 86.8 | **135.7** (190, 54.3) | 523 | 1.41 (14.5) |

Read the cases converged at a rounding > 0 with up to +4 mm (CORRIE 11.4). At 15 in meat that gives 186.1 mm,
margin >= 3.9 mm. This passes, and it is slightly better than CORRIE's 184.4 mm (margin 5.6, >= 1.6 with the bias),
because the lid sits lower than CORRIE's pouch on its roll clips. Not modelled: the module walls, the SWAP slab's
packing advantage (the sim fill is uniform; a dense sleep kit held flat at the frame by IM1-IM3 moves the real CG
forward, so this is conservative), the drawcord gather (the sim closes the collar flat, as for CORRIE) and the tripod
kit.

Loadout CG (`cache_loadout.py`: the CORRIE packer, the CORRIE peel and CACHE's zones), belt M, +15 in peel. Day
169.4, elk 159.5, sheep 179.9 (limit 205); pack-outs 136.8 / 152.9 / 149.2 (limit 190). CG z 438-518 (limit 590).

## 5. Access (loadout re-run, all loadouts x belts S-XXL; hourly / constant items must be class <= 1)

| Loadout (belt M) | CORRIE B.2 misses | **CACHE misses** |
|---|---|---|
| Day hunt | snacks | **0** |
| 6-day elk (rifle, archery) | snacks | **0** |
| 8-day sheep | GPS, 2nd bottle, snacks (+ poles at glassing) | **2: GPS (S-L belts), 2nd bottle** |

The SP strap pocket fixes snacks on every belt. The optics pod's two cinch straps carry the sit pad and poles flat
over the pod, which fixes the sheep poles at glassing. The KILL module holds the kill kit, first aid and game bags by a
packing rule (user guide, like CORRIE's IMP-4 rule; `cache_loadout.FORCE`). Still open: the sheep GPS (160 mm long) on
S-L belts and the second bottle (one holster), as for CORRIE. On sheep loads the rain jacket and pants ride in the bag
(weather class 5).

## 6. Build (beginner, one walking-foot machine)

47 cut pieces (shell 24 + modules, pods and pocket 23), **1 curved seam** (CORRIE's door corner, unchanged),
**2294 mm of zip** (#10 door 1254, #8 lid 260, #5 KILL 780), **37.9 h** on the bag_concepts beginner model
(ASSUMPTION: a ranking, not a plan). Shell 21.0 h; modules 2.2-3.1 h each. Every module is a straight tube + a boxed
floor + a folded roll hem: the easiest sewing in the pack, and a good first project before the shell. Silpoly seams are
sealed with silicone, not tape (record note).

## 7. Fixed list check

| Fixed item | CACHE |
|---|---|
| Frame interface (B-19 hood, B-20 ladders, B-22 guys, IM2/IM3 hooks with B-17/B-23, hinge pins + B-18, B-24, US1/US2, IM1-IM3, fairleads, bow riser carry, fly in its base pocket) | unchanged: CORRIE's B-01, collar frame side B-06f, hinge band and seams are used as is (`test_shell_drops_wings_rolltop_pouch`) |
| 85 L +/- 3, width <= 15.5 in, depth <= 12 in | 85.2 L design basis, 87.9 L simulated; 15.5 in; 10.2 in |
| Look / sound | body solid; camo on the kick plate, door garages, the new SH-09 hinge-band bar, the optics-pod edge bar, the lid pull tab and the module tabs; no hook-and-loop; coil zips; modules close with G-hooks (no buckle clack) |
| Loads (HA-LS-1 rev C) | section 4: all six cases pass |
| Access | section 5 |
| IP | original names and look; the removable liner is not a sewn load cell (research section 5; attorney flag) |
| Build | section 6 |

## 8. Weaknesses (stated plainly)

1. **Weight: +98.9 g against CORRIE B.2** as counted, and 4041.9 g (8.91 lb) at belt M on H1. The case for it rests on
   the stuff sacks it replaces, and the scoring does not credit that.
2. **The shell is CORRIE's.** The novelty is in the modules and the swap. The cloth sim is essentially a re-run with
   different external loads.
3. **No roll-top.** The cinched collar is not waterproof. Rain protection depends on the LID, the fly and the
   dry-bag modules (silpoly 2000 mm head, ASSUMPTION for seams sealed with silicone). The roll's volume adjustment is
   gone too: small loads rely on IM1-IM3 inside, the LID straps on top and the side straps.
4. **Module walls cost volume** (about 4 % in the model) and add handling time at camp.
5. **Kill-site sequence**: to turn the slab into the liner, the sleep kit has to go somewhere first (aft column or
   strapped under the lid straps). It is one more step than CORRIE's "meat straight onto IM1-IM3".
6. **Silpoly against bone ends and brush**: no data. The slab's frame face and floor are 70D for that reason.
7. **The door is narrow at the bottom** (198 mm at the sill, 304 mm at the hinge). The 250 mm CAMP module slides out
   above z 300 and squeezes below it. The 330 mm SWAP slab comes out through the collar, not the door.
8. **Renders**: the snack pocket is not drawn. The pod cinch straps are drawn as simple bands. The modules' shapes are
   Blender cloth with internal pressure, not a sim of real contents.

## 9. Tests proposed before a build (prototype)

| Id | Test | Pass |
|---|---|---|
| MOD-1 | SWAP liner leak: 30 kg boned meat in game bags, 2 h carry, then inspect the shell and wash the liner | no blood on the shell; liner clean after a rinse |
| MOD-2 | Silpoly / 70D abrasion: liner face against bone-in quarters, 10 km walk | no hole |
| MOD-3 | Drawcord collar + LID in rain (15 min shower test, fly off / on) | modules dry; shell top damp at most |
| MOD-4 | Module swap time at the kill site, gloves | slab to liner in under 3 min |
| MOD-5 | 15 in plumb-line CG with 30 kg on IM1-IM3 in the liner (CORRIE 11.4 asks for the same) | <= 190 mm |

## 10. Renders (Blender Cycles, `huntkit/viz3d/cycles_render.py`, 1600 x 1200, 48 samples)

How they are made: CORRIE B.2's render pack (the cloth-sim shell drape, frame, harness, belt B, display form). The
drape is cut at z 800 and a gathered collar is lofted from that ring. The LID uses CORRIE's pouch builder. The modules
are Blender cloth with internal pressure (`module_cloth_bpy.py`). The owner camo texture is rendered at true scale (one
380 mm repeat).

| # | File | View |
|---|---|---|
| 1 | `outputs/screens/20261110_bagD_1.png` | hero 3/4 rear on the display form |
| 2 | `outputs/screens/20261110_bagD_2.png` | side profile (wearer's left: optics pod) |
| 3 | `outputs/screens/20261110_bagD_3.png` | access: door open, CAMP module sliding out, KILL module out |
| 4 | `outputs/screens/20261110_bagD_4.png` | feature: the modules out (SWAP slab, CAMP, KILL) |
| 5 | `outputs/screens/20261110_bagD_5.png` | meat haul: SWAP slab back in as the liner, IM1-IM3 over it, game bags |
