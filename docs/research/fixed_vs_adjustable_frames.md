# Fixed-length vs adjustable-torso hunting frames (BL-007 research)

Owner: structural-fea-engineer, 2026-11-10. Ticket: `docs/backlog/BL-007-fixed-torso-frame.md`. Used by
`designs/pack_5200/analysis/frame_fixed_torso.md` §5 (fit consequences).

Method: web search plus a direct fetch of each maker's own page where it loaded. Where only a search snippet or a
forum was reachable, the claim is marked **secondary**. Torso length is C7 to the iliac crest in every source
that defines it, the same as `geometry.yaml` `torso_definition`.

## 1. What the leaders sell

| maker / frame | sized or adjustable frame | frame sizes | torso ranges stated | adjustment at the harness | source |
|---|---|---|---|---|---|
| KUIU Pro | **sized** (3 frame heights) | Regular, Tall, Extra Tall | Regular up to 17 in, Tall 17–19 in, Extra Tall 19 in and up | **4 in of vertical shoulder-strap height** (T-lock), lumbar pad 1.5–2 in | KUIU FAQ via search snippet (**secondary**: the FAQ page now redirects to a help centre that returned 404 on fetch) https://www.kuiu.com/pages/faq-2 ; forum quote of a contradicting chart (>17 in for Regular): https://rokslide.com/forums/threads/new-kuiu-pro-suspension-and-pro-bag-review.132719/page-12 (**secondary**) |
| Kifaru Duplex Lite / Tactical | **sized** (3 frame lengths) | 22, 24, 26 in | under 14 in: 22; 14–18 in: 24; 18 in and up: 26; "5'10–6'0 often between sizes" | sliding shoulder-harness attachment on the frame (range not published); short / long straps split at 18 in | size guide fetched: https://kifaru.net/pages/frame-size-guide (torso definition, strap split only); frame-length table from the Kifaru FAQ via search snippet (**secondary**; help.kifaru.net does not resolve from this session): https://help.kifaru.net/kb/faq.php?id=16 . A Kifaru collection page says "two sizes, 25 and 22 in" (conflict): https://kifaru.net/collections/frames |
| Exo Mountain Gear K3 | **sized + extension** (2 frames, each with a reversible extension) | Short 24–25.5 in, Tall 25–26.5 in | Short 15–17 in, Tall over 18 in, 17–18 in "gray area" | built-in shoulder-harness adjustment (range not given) plus the 1.5 in frame extension | fetched: https://exomtngear.com/pages/fitting-your-pack |
| Stone Glacier Krux / Krux Short / Xcurve | **sized** (regular and short) | Krux 26 in, Krux Short 23 in (retailer) | Krux and Krux Short "torsos under 19 in" | "micro-adjustability" by moving the shoulder-strap attachment height on the frame sheet (range not given) | fetched: https://stoneglacier.com/pages/selecting-a-hunting-frame-which-stone-glacier-frame-is-right-for-you ; 26 / 23 in heights: https://www.gearfool.com/collections/gear/products/stone-glacier-krux-frame-1 (**secondary**, retailer) |
| Seek Outside Revolution | **adjustable by bolt-on extensions** (not on the body) | 24 in base, 26 and 28 in with 2 / 4 in extensions | 24: 15–21, 26: 17–22, 28: 19–24 (product page); 16–20 / 16–22 / 16–24 (technical page) | harness moves on the frame | https://seekoutside.com/revolution-suspension-pack-frame/ and https://seekoutside.com/backpack-technical-details/BackpackDetails (both via search snippet, **secondary**) |
| Mystery Ranch (Guide Light MT etc.) | **sized frame + telescoping yoke** | S, M, L, XL (frame + belt combos) | Men's/Unisex: XS 13–18, S 15–20, M 15–20, L 17–24, XL 17–24 in; Military S 14–18, M 16–20, L 19–24 in | yoke telescopes ("macro adjusts"); chart ranges are **not** the limits, "a little extra adjustment" for layers; one owner reports a 16–18 in yoke | fetched: https://www.mysteryranch.com/fitting-and-sizing ; yoke range anecdote: https://rokslide.com/forums/threads/purchasing-mystery-ranch-yoke-alone.283790 (**secondary**) |

## 2. Findings

1. **No leader in this class adjusts the frame height on the body while worn.** KUIU, Kifaru, Exo and Stone Glacier
   sell the frame in 2–3 fixed heights; Seek Outside changes height with bolt-on extensions; Mystery Ranch sizes the
   frame and telescopes only the yoke. Our continuous on-body crown (owner, 2026-11-01, "universal fit") is unusual
   in this class, not standard.
2. **Fine adjustment lives at the harness.** The one published number for a hunting frame is KUIU's 4 in (±2 in)
   of shoulder-strap travel on each frame size. Mystery Ranch yoke ranges in its chart span 3–7 in per size
   (e.g. S 15–20, L 17–24), with overlap between sizes.
3. **Size steps.** Frame-size boundaries sit at 14 / 17 / 18 / 19 in torso (Kifaru, Exo, KUIU): a step of about
   2 in of torso per frame size, with a 1 in "gray area" overlap (Exo) or "in between sizes" note (Kifaru,
   5'10–6'0). Frame heights step 2 in (22 / 24 / 26 in Kifaru, KUIU per a non-maker page; 24 / 26 / 28 in Seek
   Outside).
4. **Covering 15–23 in.** KUIU covers it with 3 frames + 4 in harness travel; Kifaru with 2–3 frames
   (24 + 26 in); Mystery Ranch with 2–3 sizes (S/M + L/XL) and an overlapping yoke.
5. **Returns and resale.** No maker publishes return rates for wrong frame size. Kifaru and KUIU advise "when in
   doubt go taller" (KUIU, snippet, **secondary**) or deciding by torso and load (Kifaru FAQ, **secondary**).
   Mystery Ranch has a paid custom-size program for sizes off the chart (fetched page). Forum owners report
   buying a second frame or longer straps when the size was wrong (e.g.
   https://rokslide.com/forums/threads/kifaru-vs-stone-glacier-which-is-better-for-long-torsos.311708 ,
   https://rokslide.com/forums/threads/stone-glacier-packs-for-short-torsos.295723/ , **secondary**). Not
   found: resale-value data. Treat "a wrong size is a return or a re-print" as the honest planning case.

## 3. What this sets for BL-007

- ASSUMPTION (design input, from finding 2): the fixed variants get **±1.0 in (±25.4 mm)** of fine adjust at the
  yoke, half of KUIU's published 4 in, because our yoke rides on a carbon spine and every millimetre of travel is
  a strip on the spine (`frame_fixed.YOKE_ADJ_MM`). Test that settles it: fit 6 wearers at both ends of each size
  on the T9 rig with 30 lb; pass = load lifters 30–60° and belt on the iliac crest at both ends.
- Size steps of 2 in (finding 3) give **4 sizes** for 15–23 in at ±1 in; ±1.33 in would give 3 sizes.
