# Spreader (BP-06 rev B, Sandwich v2): build sheet

**This is the production spreader** (owner decision 2026-11-05, `docs/DECISIONS.md`). It is the stiff carbon
board that sits between the bag and the frame. Meat and bone ends press on it and it passes that load into the two
frame stays, so nothing hard reaches your back.

Engineering record: `designs/pack_5200/analysis/spreader.md` (checks, cost, mass) and
`designs/pack_5200/analysis/spreader_layout.md` (lean-torso re-check). Numbers below come from those files,
`designs/pack_5200/analysis/spreader_results.json` (`chosen`, key `sw110c6d`), the code in
`huntkit/gendesign/spreader.py`, a material record in `data/materials/`, or a line marked `ASSUMPTION:`.
Units are mm, with inches where it helps (1 in = 25.4 mm).

## Files in this folder

| file | what it is | use it for |
|---|---|---|
| `spreader_v2_cut.dxf` | outline, notches and 6 clip slots (layer CUT); 11 puck circles and 2 edge-tube lines (layer MARK, do not cut); label (TEXT). mm, 1:1. The doubler zones are on the PDF | CNC router or water-jet shop |
| `spreader_v2_clip.dxf` | side profile of the snap clip, extrude 10 mm, qty 6 | MJF print bureau (PA12) |
| `spreader_v2_drawing.pdf` | dimensioned drawing, 1:1 on A3, with puck heights and a 100 mm check bar | print at 100 %, check the bar, use as a bonding jig |
| `spreader_v3_*` | **not production.** The rejected d6L thin-HDPE alternative | do not cut |

## What it is

| item | value | source |
|---|---|---|
| size | 242 × 318 mm (9.5 × 12.5 in), frame z 112–430 | drawing; `spreader.py` `outline_v2` |
| thickness | 6.44 mm (0.25 in) = 6 mm core + 2 × 0.22 mm skins | record `cfrp_t300_3k_woven_epoxy_ply` ply 0.22 mm |
| mass installed | **154 g (5.4 oz)**: board 99 g, edge tubes 21 g, clips, pucks, pads, doublers and seal 34 g | `spreader.md` §4 |
| cost | about $188 per part | `spreader.md` cost table |
| checks (HA-LS-1 rev B, 2 mm grid) | first-ply SF 1.21, fatigue 1.04, sandwich local 1.06, factored lean-torso air 8.4 mm | `spreader.md`, `spreader_layout.md` |

## 1. Layup and core

From the wearer side (inner) to the bag side (outer): **twill / ROHACELL / twill.**

1. Skin: one ply of 200 g/m² 2x2 twill carbon (`cfrp_t300_3k_woven_epoxy_ply`), fibres at 0/90 to the board edges.
2. Doubler: one extra ply of the same twill at **45°** in four patches round the fairlead notches, on the core side
   of the skin: |x| 76–121 mm at z 113–219 and z 301–359 (both sides). Blue dashed on the drawing; `spreader.py`
   `doubler_zone`.
3. Core: ROHACELL 110 IG-F, **6 mm** (`rohacell_110_igf`, 110 kg/m³, closed cell). Cut it a little oversize.
4. Doubler patches again, then the second twill skin.

Wet out with laminating epoxy, peel ply on both faces, vacuum bag on a flat plate, cure at room temperature, then
post-cure at **60 °C** (`spreader.md` §3). The core must stay below **130 °C** (record `max_process_temp_c`).

- ASSUMPTION: dry the core in an oven at 60 °C for 2 h before laying up so trapped moisture does not blister the
  skins (common PMI practice; not in the record).
- ASSUMPTION: the doubler plies sit on the flat core and the bag pulls them in; no core relief is cut for the
  0.22 mm step. If the panel rocks on a flat table after cure, sand the high spots on the bag face only.
- ASSUMPTION: resin to fabric about 1:1 by mass, as for any wet layup with peel ply. `spreader.md` assumes
  0.06 kg/m² of resin soaks into the cut core cells.

## 2. Cutting

Cut the cured blank **from the DXF** (`spreader_v2_cut.dxf`, layer CUT only) on a CNC router with a compression
(up/down cut) bit, so neither skin frays (`spreader.md` §3). A water-jet shop works too.

- Tolerances: outline ±0.3 mm, slots ±0.2 mm, inside corners R ≥ 6 (drawing title block).
- Six clip slots, 4 × 16 mm, full-round ends, at x ±100 and z 166, 260, 400 (`spreader.py` `SLOT_W`, `SLOT_L`,
  `clip_slots`).
- Three notches per side for the bag fairleads at US2 z 142, IM1 z 190, IM2 z 330: 30 mm tall, root at x ±92, R6
  root corners, 6 mm of air round each cleat (`spreader.md` §3).
- Corners R20 at the top, R8 at the bottom.
- Break every cut edge 0.3 mm with fine sandpaper. Then **seal every cut edge** with two brushed coats of epoxy.
  The core is foam: the seal keeps out blood and grime (`spreader.md` §3).
- Carbon dust is an irritant and conductive. Cut wet or with dust extraction and wear a mask.
  ASSUMPTION: standard shop practice, not a project test.

Check the cut board against the 1:1 PDF before bonding anything to it.

## 3. Bonding the fittings

Adhesive: two-part toughened epoxy (`adhesive_epoxy_toughened_2part`). Abrade each bond face with 120 grit and wipe
with isopropyl alcohol first. ASSUMPTION: 120 grit and IPA are the usual composite surface prep; the record does not
name them. Use the 1:1 PDF taped to a flat board as the jig.

| part | qty | where | size | source |
|---|---:|---|---|---|
| edge tubes, pultruded carbon 10/8 mm (`cfrp_pultruded_rod_tube`) | 2 | **bag face**, along the bottom edge (z 118.5) and the top edge (z 424) | 236 mm long | `spreader.py` `EDGE_TUBES`; drawing |
| pucks, printed PAHT-CF (`pa12_cf_fdm_paht`), Ø16 mm | 11 | **wearer face**, where the board crosses a branch (x ±84 z 240, x ±73 z 285, x ±73 z 365, x ±82 z 405) or the bar (x −36, 0, 36 at z 330) | heights 3.0, 1.5, 1.2, 2.2 mm (branches, same both sides) and 6.7 mm (bar) | `spreader.py` `puck_table` (local gap − 0.3 mm); drawing |
| stand-off pads, PAHT-CF | 2 | **wearer face**, bottom tab, x ±115, z 119 | 16 × 10 × 4.9 mm | `spreader.py` `PAD_Z`; height = stay radius at z 260 − at z 119 |
| EVA rub strip, 1 mm | 2 | **wearer face**, over each stay line, x ±115 | 8 mm wide, full height | `spreader.md` §3 |

The pucks are cut to the measured gap less 0.3 mm, so the board bears on the frame as soon as it is loaded
(`spreader.md` §3). Print the pucks a little tall and sand them to the height on the drawing.

## 4. Where it mounts

- On the **bag side** of the two printed stays, bag face up, between the bag and the frame (`DESIGN.md` §4.10,
  `docs/CONTRACTS.md` §6).
- Six **MJF PA12 snap clips** (`spreader_v2_clip.dxf`, PA12 record `pa12_mjf_hp`) snap over the stays at z 166, 260
  and 400. The inboard leg of each clip goes through its slot; the outboard leg passes outside the board edge.
- The bottom tab rests on the two pads at z 119, where the stay is thinner.
- No bolts and nothing bonded to the frame. To wash: pop the six clips and lift the board out.
- The frame under it is the **socket-free** branch body in `designs/pack_5200/print/frame/`. Do not fit it to a
  frame printed with the d6L stay sockets: the cups stand 1.8 mm proud of the crown plane, where the board sits
  (`PRODUCTION.md`).

## 5. Check before use

- Mass of the finished board with tubes, pucks and pads, without clips: about 141 g. ASSUMPTION: 154 g installed
  less 6 clips at 2.1 g each (`spreader_results.json` `clip_mass_g`). Much heavier means too much resin.
- Coin-tap the whole board. A dull sound means a skin is not bonded to the core: do not use it.
- First article: the bone-end proof in `designs/pack_5200/print/frame/PRODUCTION.md` (400 N through a 22 mm dowel
  at the window centre, the US2 corner relief and the IM1 notch root).
