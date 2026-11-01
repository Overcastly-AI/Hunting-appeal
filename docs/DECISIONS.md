# Decisions log

| Date | Decision | By | Notes |
|---|---|---|---|
| 2026-11-01 | Original camo/designs only; KUIU is a performance benchmark only | owner+Claude | |
| 2026-11-01 | First pack = 5200 cu in (85.2 L) framed hunting pack, 150 lb rated | owner | |
| 2026-11-01 | Carbon fiber frame | owner | Must be buildable without an autoclave (bought tubes and plate, bonded joints) |
| 2026-11-01 | "Universal" fit: one pack adjusts to fit everyone | owner | Interpreted as: wide continuous torso adjustment, interchangeable hipbelt sizes, harness that works for men and women |
| 2026-11-01 | Builder is a first-timer with no machine yet | owner | Need: equipment buy list, beginner build guides with practice drills, plus factory-quotable tech packs for mass production |
| 2026-11-01 | Mostly solid colors; camo as ACCENT panels only | owner | Edgy and unique, but functional, lightweight and rugged. Accent panels sit in high-wear/articulation zones (yokes, forearms, knees, seat, pack lid/pockets/hipbelt wings); the edgy look comes from functional angular seam lines, not decoration |
| 2026-11-01 | Primary mission is PACKING ANIMALS OUT (meat hauling) | owner | Drives the load shelf, frame-only haul mode, tall-load geometry, head/antler carry and blood-tolerant materials. Claude's recommendation (adopted, owner can override): keep the 150 lb rating and add a 200 lb overload case at SF ≥ 1.5 |
| 2026-11-01 | BASE CAMO = owner-supplied SVG ("Owner Base", 1000×1000, 4 colors: #ae9d6c base tan, #8b8148 olive, #c6b497 light tan, #313120 dark) | owner | Replaces Cirquefall as the primary pattern. Cirquefall stays as an alternate. Master file goes in designs/apparel/camo/source/owner_base.svg (owner to upload byte-exact). Structure: macro blobs traced on a ~5.56 px grid, plus digital pixel overlays at 15.6 and 7.8 px |
| 2026-11-01 | Ambidextrous carry: rifle carry and side-zip access on both sides | owner | Adds an estimated 60–90 g plus sewing ops |
| 2026-11-01 | One bag height for now; short bag (15–17 in torso) is a later option | owner | |
| 2026-11-01 | Tall-load extension posts are a separate ACCESSORY | owner | Frame keeps the sockets |
| 2026-11-01 | Torso adjust: owner asked for a pulley-buckle system instead of pin holes. Under evaluation: pulley-tensioned telescoping crown with positive lock backup | owner+Claude | Gives continuous, on-body adjustment; must hold drop loads without creeping |
| 2026-11-01 | First pack bag design REJECTED: too boxy/dated, wrong bag shape/profile, wrong features/layout. Frame/suspension concept not objected to | owner | Root cause: no market research. Fix: research phase (docs/research/) before redesign. Owner's favorite benchmarks: Stone Glacier, Exo Mountain Gear (performance benchmarks only; no copying the look) |
| 2026-11-01 | Bag redesign direction A "Spine": slim teardrop roll-top, ~10 in deep, diagonal front panel, camo accents; 5.0 lb total target | owner | From docs/research/pack_market_2026.md. Frame and pulley crown kept |
| 2026-11-01 | Frame strength standard: MATCH THE LEADERS. Realistic field loads, verified by physical prototype load tests; frame target ~550–700 g | owner | Replaces the 7-case SF 2.0 standard (which needed 1103 g). Exact factors go in designs/pack_5200/analysis/load_standard.md with cited basis |
| 2026-11-01 | IP: extension posts are LASH/FLAG POINTS ONLY; load lifters never relocate onto posts | Claude | Avoids Mystery Ranch US 10,952,523 claim scope. Patent attorney review before tooling |
| 2026-11-01 | Add GENERATIVE DESIGN to the frame: topology-optimized 3D-printed Ti/Al node lugs (bonded to carbon tubes), a topology-optimized water-jet carbon lumbar/hipbelt plate, and ground-structure layout optimization. No full one-piece generative frame for now (tooling cost, field repair) | owner idea + Claude scoping | New package huntkit/gendesign/ |
| 2026-11-01 | 3D PRINTING is first-class: two tiers for every printable part. SLM Ti/Al for production (online service); desktop CF-nylon for prototypes (owner's printer). Printable hardware: lugs, hipbelt pivot mount, crown rack/pawl, pulley guides, later shelf hooks, rod clips, sewing jigs. Files go in designs/pack_5200/print/ | owner | Owner to confirm whether "3D printed" also means printing the whole frame |
| 2026-11-01 | Volume: TRUE 85 L in the main bag alone; allow ~11.5–12 in depth so the bag is ~42 in tall | owner | Overrides the 10 in depth from Direction A |
| 2026-11-01 | Single diagonal zip (no side zips) | owner | |
| 2026-11-01 | Rain fly counts in the advertised base weight | owner | |
| 2026-11-01 | Load standard HA-LS-1 adopted; frame v2 = 577 g (straight stays, carbon wraps, hat lumbar pan) | Claude (per owner "match leaders") | Crush coupon T7 must pass before relying on the bushing-contact credit |
| 2026-11-01 | Generative design result: printed Ti lugs are +194 g vs carbon wraps, so KEEP carbon wraps; Ti hip-pivot mount only (-8 g). Printed parts used for crown rack/pawl, pulley guides and prototypes | Claude | See analysis/generative_design.md |
| 2026-11-01 | CORRECTION: generative design applies to the WHOLE FRAME as one topology-optimized 3D-printed structure (fully plastic acceptable), not the joints | owner | Study: analysis/printed_frame_study.md compares FDM PA-CF, SLS PA11/12, continuous-fiber printing, SLM Al vs the 577 g tube frame; covers mass, stiffness, creep, fatigue, printability |
