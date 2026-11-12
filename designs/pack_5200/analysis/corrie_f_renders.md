# CORRIE F renders (BL-012): shot list and defect log

Date: 2026-11-12. Ticket: `docs/backlog/BL-012-renders.md`.

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
