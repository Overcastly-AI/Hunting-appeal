# CORRIE F renders (BL-012): shot list and defect log

Date: 2026-11-12. Ticket: `docs/backlog/BL-012-renders.md`.

> **Update, BL-026 (2026-11-12): the set was re-rendered as rev 1 on the final H1 body.** Section 8 is the current
> shot list and defect log (`outputs/screens/20261112_BL026_<n>.png`). Sections 1 to 7 are the BL-012 record and
> are kept as written; where they say "rev 0", "18 mm cheek" or "38 mm straps", section 8 supersedes them.

These are **rendered 3D models, not photographs**, and nothing here is an engineering number: the module
builds presentation geometry on CORRIE F's fine cloth-sim drape. Dimensions quoted below are measured from
the built scene meshes (`outputs/corrie_f_viz/<state>/*.glb`) and are picture checks only.

## 1. What is shown

| Item | Shown | Note |
|---|---|---|
| Bag | CORRIE F, door **D2**, no wings, no crown hood | `huntkit/viz3d/corrie_f.py` on the BL-020 cloth pass |
| Bag revision | **rev 0** | Rev 1 (2026-11-12) is **not** shown, see section 4 |
| Frame | H1 printed body, carbon crown at 19 in | IM3 fairlead cheek drawn at the released 18 mm; the design value is 28 mm (BL-021) |
| Belt | Hipbelt B, pocket left, bottle holster right | |
| Hunter | 1829 mm (6 ft) man, 19 in torso setting (BL-019) | `analysis/hunter_figure.md` |
| Settings | 1600 x 1200, 64 samples, Cycles CPU | 110 to 180 s a frame on 4 shared cores |

How to regenerate (needs the bpy venv and the human assets, both outside the repo):

```
export HUNTKIT_BPY=<scratch>/bpyenv/bin/python
export HUNTKIT_HUMAN_ASSETS=<scratch>/human_assets
python designs/pack_5200/concepts/corrie_f_viz3d.py --render hero,door   # one or more shots
python designs/pack_5200/concepts/corrie_f_viz3d.py --sheets --docs
```

## 2. Shot list

Files are `outputs/screens/20261112_BL012_<n>.png` (all under 1.5 MB). "Ticket" is the shot number in BL-012.

| n | Shot | Ticket | Subject | Status |
|---|---|---|---|---|
| 1 | hero | 1 | 3/4 rear on the hunter, 6-day load (45 L) | done (re-rendered, D-2) |
| 2 | side | 2 | Side profile on the hunter, 6-day load | done (re-rendered, D-2) |
| 3 | day | 3 | Day load (12 L), rolled down, pouch off | done (re-rendered, D-2) |
| 4 | full | 4 | Full, 85 L class, collar standing | done (re-rendered, D-2) |
| 5 | walk | owner update | Hunter walking uphill with poles, outdoors | done |
| 6 | kneel | owner update | Hunter kneeling and glassing, outdoors | done |
| 7 | door | 6 | Door D2 open, full load | done |
| 8 | meat | 7 | Meat inside the bag on IM1 to IM3, door open | done |
| 9 | frame | 8 | Bag off, meat on the H1 frame | done |
| 10 | frame_bare | 8 | Bag off, bare H1 frame, crown, spreader, belt | done (caption corrected to 28 mm) |
| 11 | addons_on | 9 | Tripod (right), scope pod (left), from the right | done (new) |
| 12 | addons_on_left | 9 | Same, from the left: the scope pod | done (new) |
| 13 | addons_off | 9 | Base pack, same camera as 11 | done |
| 14 | belt | 10 | Hipbelt B and pockets, front 3/4, on the hunter | done |
| 15 | roll | extra | Rolled closure and top pouch | done |
| 16 | sheet | task 4 | **CORRIE B.2 against CORRIE F**, same camera, full load | done (new) |
| 17 | sheet | acceptance | Day, 6-day and full side by side, same camera | done (rebuilt) |
| 18 | sheet | 9 | Add-ons on and off side by side | done (new) |
| 19 | compare_f | task 4 | CORRIE F frame of the comparison | done |
| 20 | compare_b2 | task 4 | CORRIE B.2 frame of the comparison | done (new) |
| - | door D1 | 5 | Door D1 open | **not rendered** (section 4) |

Copied to `docs/screens/` (best six): 1 hero, 5 walk, 6 kneel, 7 door, 16 comparison sheet, 17 load-state sheet.

## 3. Defect log

Every image was opened and inspected after rendering. "Fixed" means the file now on disk shows the fix.

### 3.1 Fixed in this pass

| ID | Shot | Defect | Fix |
|---|---|---|---|
| D-1 | 10 | Caption said the IM3 cheek is "27 mm since 11-11"; BL-021 set it to 28 mm on 11-12 | Caption and `frame_note()` text corrected; frame re-captioned from its raw render (no re-render) |
| D-2 | 4 (and 1, 2, 3) | The full load's collar and top pouch were cut off at the top of the frame; the side shot cut the boots | `HUNTER_ZOOM` 1.3 to 1.16 for the four standing shots, which share one camera box; all four re-rendered |
| D-3 | 18 | The sheet named the top pouch as an add-on, but the "off" frame also carries it | Sheet subtitles reworded: the pouch belongs to the base pack in both frames |

### 3.2 Checked, not a render defect

**D-4, "the bag looks like it sits off the frame" (hero, full, comparison).** Measured on the 6-day scene:
the bag's frame face sits within -5 to +3 mm of the spreader pucks and frame legs from z 120 to 420 mm
(it is in contact; negative means the cloth is drawn a few mm into the part). There is no air gap between
bag and spreader.

What the eye reads as a gap is real geometry of the design. The back panel is 370 mm (14.6 in) wide
(x +/-185) and black, the frame legs stop at x +/-139, and the bag's frame face stands 36 to 46 mm
(1.4 to 1.8 in) aft of the back panel. So outboard of each frame leg there is a 46 mm wide open slot, about
40 mm deep, with a black panel edge beside it. From 3/4 rear that slot shows as a dark slab standing clear
of the bag. Nothing was changed, because closing it would change the design (out of scope). Options are in
section 5.

### 3.3 Open defects (not fixed)

| ID | Shot | Defect | Why not fixed |
|---|---|---|---|
| D-5 | all | Rev 0 is drawn: guys at about x +/-100 with bar loops and toggles; no B-25 bridle, no B-26 tripod keeper cord | `huntkit/viz3d/corrie_f.py` has no revision switch; the guy geometry comes from the legacy builder. Moving it needs new geometry and a re-render of every pack shot |
| D-6 | 9, 10 | IM3 fairlead cheek drawn at 18 mm, design is 28 mm; under-straps in shot 9 drawn 38 mm, design is 25 mm (BL-003) | The H1 mesh in `outputs/pack3d_h1` is the released body; both are stated in the captions |
| D-7 | 11, 12 | W3 passes below the scope pod's base and bridges about 60 mm of air between the pod and the bag corner | The pod is placed by the legacy carry builder; needs a re-route of W3 over the pod |
| D-8 | 11, 12 | The scope pod is a smooth rounded sleeve with no seams, zip or drape wrinkles | Rounded, not a slab, but it is the plainest part in the set |
| D-9 | all pack shots | The bag's front face penetrates the spreader cross tubes by up to 15 mm at two points (z 120 and 420, x 110) | Hidden between bag and frame in every shot; only measurable |
| D-10 | 5, 6 | Outdoor ground is a flat plane with repeated grass; the walk shot's slope is a tilted plane; the figure's face and hands are plainly synthetic | Limits of the CC0 assets (BL-019) |
| D-11 | 14 | Shoulder strap edge at the hunter's left shoulder shows a jagged mesh edge (about 30 px) | Wearer strap fit from BL-019; a `wearer.py` change, outside this ticket's files |
| D-12 | 7, 8 | The opened door hangs as a stiff flap with the door pocket on it, more like a board than cloth | The open door is a hinged rigid copy of the solved door panel, not a second drape |
| D-13 | 3 | Day load: the cloth is heavily crumpled and the W straps cut across it; it reads slack rather than cinched flat | That is the solved cloth at 12 L in an 85 L shell. See section 5 |

No image shows floating parts, z-fighting, blocky or stretched camo, or placeholder blocks. The acceptance
line "no intersecting geometry" is met for everything visible; D-9 is a hidden intersection.

## 4. Not done, and why

1. **Door D1 open (ticket shot 5).** The model builds door D2 only (`Provider.viz_door`, `d2_recut`). D1
   needs its own re-cut of the aft face and its own zip path. Not attempted in this pass.
2. **Rev 1.** `designs/pack_5200/concepts/corrie_f.py` has `revision(1)`, but the picture model does not
   read it. All shots are rev 0. Visible difference at rev 1: the two guys move inboard to x +/-52 on a
   bridle round the top bar, and one 3 mm cord crosses the right gusset. Neither changes the silhouette.

## 5. Proposals (design or follow-up, not applied)

1. **Frame slot (D-4).** Pick one: (a) body-colour edge binding on the back panel so the slot stops reading
   as a black slab; (b) trim the back panel to the frame-leg width plus a margin; (c) leave it, as every
   external-frame pack shows its frame depth from this angle. This is a look question; it needs an owner
   decision because (b) changes the back-panel pattern.
2. **Day load (D-13).** At 12 L the shell has far more cloth than load. If the day-load look matters, a
   fourth compression point or a fold-and-clip rule for the lower bag would flatten it. Propose as a
   separate ticket.
3. **Follow-up render ticket** for D-5, D-6, D-7 and the D1 door once the H1 body is re-released (BL-024),
   so the frame, cheek and straps are redrawn once.

## 6. Assumptions that govern the pictures

Declared in `huntkit/viz3d/corrie_f.py`:

- ASSUMPTION CLIP-1: roll-clip tab 150 mm below the collar seam. Settled by rolling the first prototype at
  day and 6-day loads and marking where the roll ends land.
- ASSUMPTION POUCH-1: the top pouch as a limp, part-full bag. Settled by a photograph of the sewn pouch
  with 1 kg in it.
- ASSUMPTION: toggle 9 x 34 mm and a 22 g wiregate envelope 58 x 36 mm. Settled by the purchased parts.


## 7. Tests

`python -m pytest -q tests/test_viz3d_corrie_f.py`: **6 passed, 1 failed** (2026-11-12, with the bpy venv).

The failure is `test_scene_builds_as_corrie_f`. It builds the **day** scene and checks the camo blade U
against bounds that only the fuller states meet. Not fixed in this pass; the test file is unchanged.

| Check on the camo blade U | Bound in the test | Day (test, level 1) | Day (rendered) | 6-day (rendered) | Full (rendered) |
|---|---|---|---|---|---|
| Lowest point z, mm | < 80 | 105 | 96 | 81 | 44 |
| Width across x, mm | > 330 | 304 | 320 | 365 | 377 |

At the day load the solved floor lifts and the bag draws in, so the strip sits higher and narrower. The
camo piece is present and whole in the day render (shot 3). The fix is a choice: run the check on the
6-day scene with bounds re-set (81 mm also misses "< 80"), or set day-state bounds. The day blades are also
15 mm off-centre (x -168 to +152), which is the crumpled cloth, not a pattern asymmetry.

## 8. BL-026: rev 1 on the final H1 body (2026-11-12)

Ticket: `docs/backlog/BL-026-renders-rev1.md`. Code: `huntkit/viz3d/corrie_f.py` (section "rev 1"),
`huntkit/viz3d/wearer.py` (strap fit), `designs/pack_5200/concepts/corrie_f_viz3d.py`. These are still
**rendered 3D models, not photographs**, and nothing here is an engineering number. Dimensions below are measured
from the built scene meshes (`scene.report["rev1"]`, full load with the add-ons) and are picture checks only.

### 8.1 What changed in the picture

| Item | Before (BL-012) | Now | Measured on the scene |
|---|---|---|---|
| Frame body | H1 of 2026-11-10 (`outputs/pack3d_h1`), IM3 cheek 18 mm | **H1-G0.55-B1/2.5** (`print/frame_h1/h1_assembled.stl`, BL-027): thicker mid bar and upper branches, BL-024 lower-body growth, **28 mm IM3 cheeks** | same mesh as the print file (268,496 faces, one closed shell) |
| Top guys | x about +/-100, bar loop and toggle | **x +/-52** on the **B-25 bridle**: a 25 mm sleeve round the top bar each side, joined under the bar, bright toggle at each sleeve | sleeves x 39.5 to 64.5 mm; guy 363 / 375 mm (14.3 / 14.8 in) from the sleeve round the bag's top corner to B-22 |
| Tripod keeper | not drawn | **B-26**: 3 mm shock cord across the right gusset at pattern height z 600, seam to seam | span 200 mm (7.9 in), 265 mm over the tripod; on the bare gusset it lies on the cloth |
| Meat straps IM1 to IM3, under-straps US1 / US2, cradle | 38 mm | **25 mm** (BL-003), 25 mm cam buckles | 5 parts, 12 strap runs redrawn from their recorded paths |
| Back panel | black edge | **edge bound in body colour**, 12 mm on each face (ASSUMPTION BIND-1) | 1620 mm (63.8 in) loop round the 370 x 440 mm panel |
| Scope pod | smooth capsule, no seams | sleeve with a flat sewn base, base seam, bound mouth, 90 mm No. 5 throat zip (ASSUMPTION POD-1) | base z 115, mouth z 520, radius 50 mm |
| Straps over the pod | lowest strap crossed the pod's rounded base and bridged about 60 mm of air | pod hangs 75 mm lower; **W1 re-run taut over the pod's wall** | W1 on the pod at z 191 to 232, wall starts at z 133 |
| Open door | hinged rigid copy of the door panel | **cloth**: laid from the hinge seam along the taut line over hinge band, collar, roll and top pouch, 14 mm of slack bellying out of the rise (ASSUMPTION DOOR-OPEN-1); the door pocket follows it | door top z 1071 (5 mm over the pouch), free end resting on the pouch at y 157 |
| Shoulder-strap edge (D-11) | sawtooth along the strap pocket's edge at the hunter's left shoulder | fixed in `wearer.fit_pack` | see 8.3 |

### 8.2 Shot list

Files are `outputs/screens/20261112_BL026_<n>.png`, 1600 x 1200 at 64 samples, all under 1.5 MB.

| n | Shot | Subject | Status |
|---|---|---|---|
| 1 | hero | 3/4 rear on the hunter, 6-day load (45 L) | done |
| 2 | side | Side profile on the hunter, 6-day load | done |
| 3 | day | Day load (12 L), rolled down, pouch off | done |
| 4 | full | Full, 85 L class, collar standing | done |
| 5 | door | Door D2 open, full load, door drawn as cloth | done |
| 6 | meat | Meat inside the bag on IM1 to IM3, door open | done |
| 7 | frame | Bag off, meat on the H1 frame, 25 mm straps | done |
| 8 | frame_bare | Bag off: final H1 body, crown with the B-25 bridle, spreader, belt | done |
| 9 | addons_on | Tripod (right) under W1 to W3 and the B-26 cord, scope pod (left) | done |
| 10 | addons_on_left | Same from the left: the scope pod, W1 and W2 over its wall | done |
| 11 | addons_off | Base pack, same camera as 9 | done |
| 12 | belt | Hipbelt B and harness from the front 3/4 (shows the D-11 fix) | done |
| 13 | sheet | Day, 6-day and full side by side, same camera | done |
| 14 | sheet | Add-ons on and off side by side | done |

Not re-rendered (BL-012 files stand, they still show rev 0): walk, kneel, roll close-up, the B.2 comparison. Door D1
is still not modelled (section 4).

Copied to `docs/screens/` (best six): 1 hero, 5 door, 6 meat, 8 bare frame, 13 load-state sheet, 14 add-on sheet.

### 8.3 Defect log against section 3.3

| ID | Defect | Status after BL-026 |
|---|---|---|
| D-5 | Rev 0 drawn | **Fixed.** Guys on the B-25 bridle at x +/-52, B-26 cord drawn |
| D-6 | 18 mm cheek, 38 mm straps | **Fixed.** Final H1 body; meat, cradle and under-straps 25 mm |
| D-7 | Strap under the pod's base | **Fixed** for the strap that had the defect. Section 3.3 called it W3; it is **W1** (W1 is the lowest wrap, W3 the top one at z 700). W1 and W2 now cross the pod's wall. W3 runs 35 mm above the top of the scope (z 656) and does not touch the pod: the pod and scope are 541 mm long and would have to reach z 715 for W3 to bear on them |
| D-8 | Pod a plain capsule | **Fixed.** Base seam, mouth binding, zip, fabric wrinkles |
| D-9 | Bag face 15 mm into the spreader tubes (hidden) | Open, unchanged. Also measured now: the cloth-pass frame face is drawn 0 to 17 mm into the crown top bar at z 690 to 712 (hidden in every pack shot from behind) |
| D-10 | Outdoor ground, synthetic face | Open, shots not re-rendered |
| D-11 | Jagged shoulder-strap edge | **Fixed.** Cause: the strap pocket (IMP-6) is wider than the strap; the grid cells where it overhangs the pad were pulled onto the body on their own, by the pad's thickness, which tore its edge. Cells within 14 x 8 grid cells (about 36 mm) of a pad now move with the pad (`wearer._dilate`, `RIDE_AZ`, `RIDE_U`). Before / after close-ups were checked; belt and harness are otherwise unchanged |
| D-12 | Open door a board | **Fixed** as geometry (8.1). It is a constructed drape, not a second cloth solve |
| D-13 | Day load crumpled | Open, unchanged (design question, section 5 item 2) |

New, seen in this pass:

| ID | Shot | Defect | Status |
|---|---|---|---|
| D-14 | 3 | At the day load the right gusset is cinched to 79 mm at the keeper's height, so a real B-26 cord (cut for 80 % of 214 mm) would hang slack; it is drawn taut on the folds | Open, picture only |
| D-15 | 8 | The B-25 bridle tabs are drawn hanging on the wearer's side of the bar with the bag off; with the bag on only the toggles are drawn, because the cloth-pass frame face overlaps the bar there (D-9) | Open, picture only |

### 8.4 Finding for the design (not fixed here)

`corrie_f.guy_geometry()` (BL-022) measures the rev 1 guy as a **straight line** from x 52 on the bar to the B-22 tab
on the aft face (x 149, y 236, z 695): 244 mm long, outboard share 0.41, 59.7 mm from the lifter webbing. With the
bag full that line passes through the bag: B-22 is on the far side of a 380 mm wide, 240 mm deep body. In the 3D
model the guy has to leave the bar outboard, pass the crown corner and wrap the bag's top side corner, 363 to 375 mm
long. On that path it crosses the lifter band (x 91 to 119 on the bar) at the bar, which is the clash rev 1 moved the
sleeves inboard to avoid, and its pull on the sleeve is almost all along the bar. The bridle still stops the sleeve
sliding. This is a picture-model observation, not an analysis; the test that settles it is the prototype crown fit
with the bag packed full and both guys toggled.

### 8.5 Assumptions added (declared in `huntkit/viz3d/corrie_f.py`)

- ASSUMPTION BIND-1: the back-panel binding shows 12 mm on each face. Settled by the binding tape picked for the
  back-panel pattern.
- ASSUMPTION POD-1: pod sleeve 405 mm with a flat base (corner radius 18 mm), bound mouth, 90 mm No. 5 zip, base
  75 mm lower than the BL-020 obstacle. Settled by the IMP-1 pod pattern and a fit check with the owner's spotter.
- ASSUMPTION DOOR-OPEN-1: the opened door is thrown up over the top and lies on roll and pouch. Settled by a
  photograph of the first sewn bag with the door open.

### 8.6 Tests

`python -m pytest -q tests/test_viz3d_corrie_f.py tests/test_viz3d_wearer.py` with the bpy venv: **16 passed, 2 skipped**
(the two skips are wearer tests that need assets not in this session); the six viz3d test files together: 98 passed,
3 skipped. `test_scene_builds_as_corrie_f` now passes: its blade-U check uses **day-state bounds** (lowest
point < 115 mm, width > 290 mm; measured 105 mm and 304 mm at level 1) and it also checks the rev 1 parts (sleeves
centred on x 52, guys reaching the bag's corner, the keeper on the right gusset, every meat and under-strap run at
25 mm, the binding on the panel's outline, the BL-027 frame note). New tests that run without Blender: the taut-line
hull against a closed-form case, the 25 mm redraw, the binding's size and facing, the frame folder, the pad grid.

