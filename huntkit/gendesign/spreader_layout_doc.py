"""Markdown record for the spreader layout study: designs/pack_5200/analysis/spreader_layout.md."""
from __future__ import annotations

from pathlib import Path

from huntkit.fea.materials_bridge import REPO_ROOT

from . import spreader as S
from . import spreader_layout as L

ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "meat_straps", "tall_load",
         "overload_haul", "tall_load_posts", "hipbelt_off_abuse")


def _f(v, nd=2):
    return "—" if v is None or v > 1e6 else f"{v:.{nd}f}"


def _yn(b):
    return "yes" if b else "**no**"


def write_doc(ctx: dict) -> Path:
    rows, best, ch = ctx["rows"], ctx["best"], ctx["chosen"]
    fin = {r["sheet"]: r for r in ctx["final"]}
    h15 = fin["hdpe15"]
    m, c = ctx["mass"], ctx["cost"]
    base = next(f for f in ctx["frames"] if f["key"] == "base")
    frc = next(f for f in ctx["frames"] if f["key"] == ch.key)
    sh = L.sheets()["hdpe15"]
    p15 = ctx["pitch"]["hdpe15"]
    p24 = ctx["pitch"]["hdpe24"]
    s_rng = (min(r["s_walk"] for r in p15), max(r["s_walk"] for r in p15))
    lines = [
        "# Spreader layout study (BP-06 rev C): change the frame so a thin sheet works",
        "",
        "Owner decision 2026-11-05: support the sheet the way the leaders do (Mystery Ranch 0.060 in HDPE, "
        "Kifaru 1/16 in, Seek Outside removable cross stays). Sandwich v2 (`spreader.md`, 154 g, $188) is the fallback. "
        "Code: `huntkit/gendesign/spreader_layout.py` (model), `spreader_layout_report.py` (this record). "
        "Solver: `huntkit/fea/plate_grid.py` (`solve_von_karman`, new: large deflection, verified in "
        "`tests/test_plate_vk.py`). Frame FEA: `frame_production.verify_solid`, 2 mm voxels, all HA-LS-1 rev B cases. "
        "Tests: `tests/test_spreader_layout.py`. Research: `docs/research/spreader_research.md` (leaders), §9 below (HDPE data).",
        "",
        "## Recommendation",
        "",
        f"**Best thin-sheet layout: {ch.key}, {ch.name}, with a {sh.name} sheet.** It is the only layout tested that "
        "keeps a 1/16 in-class sheet off the back on every bone position, the lean torso included.",
        "",
        f"- Installed mass **{m['total_g']:.0f} g ({m['total_g'] / 28.35:.1f} oz)**: frame +{m['frame_delta_g']:.0f} g "
        f"(printed sockets), sheet {m['sheet_g']:.0f} g, 6 clips with saddles {m['clips_g']:.0f} g"
        + (f", {len(ch.tubes)} removable carbon cross stays {m['tubes_g']:.0f} g" if ch.tubes else "") + ". "
        f"Today's part is 203 g; sandwich v2 is 154 g.",
        f"- Cost about **${c['total']:.0f}** against about $188 for the sandwich. The sheet is cut by hand or CNC from "
        "framesheet stock; the carbon stays are bought tube cut to length.",
        f"- Frame, all HA-LS-1 rev B cases, 2 mm: min SF **{frc['sf_min']:.2f}** ({frc['governing']}), fatigue "
        f"**{frc['sf_fatigue']:.2f}**, creep-rupture {frc['sf_creep']:.2f} (today's body {base['sf_min']:.2f} / "
        f"{base['sf_fatigue']:.2f}).",
        f"- Carbon cross stays under the factored bone: SF **{h15['rib_sf_fact']:.2f}**, fatigue **{h15['rib_sf_fatigue']:.2f}** "
        f"({h15['rib_where']}).",
        f"- No bottoming: walking air **{h15['clear_walk_min']:.1f} mm** (≥ 3), factored **{h15['clear_fact_min']:.1f} mm**, "
        f"factored on the lean torso **{h15['clear_fact_lean_min']:.1f} mm** (≥ 0). Worst at {h15['clear_where']}.",
        f"- Skin pressure {h15['skin_peak_kpa']:.1f} kPa (≤ 14). Sheet under the factored meat alone: SF "
        f"{h15['sf_sheet_meat_only']:.2f} on the 40 °C yield (99th percentile).",
        "- Washable: pop 6 clips, lift the sheet out, pull the 6 stays out of their sockets, hose the frame. Nothing bonded.",
        "",
        "**It is heavier than the sandwich, and it needs an owner call on the bone rule.**",
        "",
        f"1. Mass: {m['total_g']:.0f} g against 154 g. The carbon stays ({m['tubes_g']:.0f} g) are what a thin sheet "
        "costs on a ventilated back. Two or four stays are not enough: the factored meat pressure alone yields 1.5 mm "
        "HDPE in a 100–160 mm bay and bulges it onto the back (table 2). It takes about 50 mm pitch.",
        "2. Bone rule: under a 22 mm bone end the HDPE stress is local to the patch and the layout cannot remove it. On a "
        f"rigid support grid from 40 to 136 mm pitch the walking stress in 1.5 mm HDPE only moves from {s_rng[1]:.0f} to "
        f"{s_rng[0]:.0f} MPa (yield {sh.yield_hot():.1f} MPa at 40 °C, 1e5-cycle fatigue {sh.fat_allow():.1f} MPa); 2.4 mm "
        f"HDPE is still at {p24[-1]['s_walk']:.0f}–{p24[0]['s_walk']:.0f} MPa. So no thin sheet passes HA-LS-1's bone rule "
        "as written (no yield at 3.0× the static bone). The leaders ship HDPE that dents under a bone and recovers; "
        "nobody publishes a bone rule (research §1, load_standard.md §1).",
        f"3. The sandwich's lean-torso miss (−0.9 mm) was in the lumbar zone (x 24, z 124), where the back rests on the "
        "lumbar pan, not in the free gutter. With the pan in the skin model (`spreader_layout.skin_ref`) the sandwich "
        f"clears by **{ctx['sandwich']['clear_fact_lean_min']:.1f} mm** (factored, lean), {ctx['sandwich']['clear_walk_min']:.1f} mm "
        "walking. It now passes every check, the strict bone rule included.",
        "",
        "So the choice is the owner's: **sandwich v2, 154 g, $188, strict rule** or **HDPE on 6 carbon stays, "
        f"{m['total_g']:.0f} g, ${c['total']:.0f}, washable, barrier rule.** On mass alone the sandwich wins. The thin-sheet "
        "files below are complete; the sandwich files in `designs/pack_5200/cut/spreader/spreader_v2_*` are kept.",
        "",
        "The barrier rule used for the thin sheet:",
        "",
        "1. The frame, sockets and carbon stays are the load path: full HA-LS-1 (SF ≥ 1 factored, fatigue ≥ 1).",
        "2. The sheet must not bottom (walking ≥ 3 mm, factored ≥ 0, factored lean torso ≥ 0), must keep skin pressure "
        "≤ 14 kPa, must not yield under the factored meat pressure alone (99th percentile, as the frame FEA), and must "
        "not puncture: local strain at the bone-patch rim (Neuber, elastic-perfectly plastic, 40 °C yield) ≤ half the "
        "elongation at break.",
        "3. Local yielding under a bone end is allowed. **Physical test T8 (new, before release):** 400 N through a 22 mm "
        "dowel at the worst bay centre and at the IM1 notch root, 10 min hold, then 10,000 cycles 0 → 213 N. Pass: no "
        "crack or craze line, residual dent ≤ 2 mm after 1 h, the dowel never reaches the rail plane.",
        "",
        "## 1. Why the layout cannot fix the bone stress (pitch study)",
        "",
        "Bone end at the centre of a square bay of a sheet on a rigid grid of line supports, held in-plane at the edges, "
        "von Kármán solve (`spreader_layout.pitch_study`).",
        "",
        "| sheet | pitch mm | walking MPa | factored MPa | factored dimple mm |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, rs in (("HDPE 1.5", p15), ("HDPE 2.4", p24)):
        for r in rs:
            lines.append(f"| {key} | {r['pitch']:.0f} | {r['s_walk']:.1f} | {r['s_factored']:.1f} | {r['w_factored']:.1f} |")
    lines += [
        "",
        "Linear Kirchhoff plate theory over-predicts these by 2–6× at the wide pitches (membrane action carries the "
        "bone once the dimple is a few sheet thicknesses deep). That is why the old linear check said HDPE needs ribs "
        "every few cm. The large-deflection solve says the opposite: pitch matters for deflection, not stress.",
        "",
        "## 2. Layout options (HDPE 1.5 mm, real frame, named + bay-centre bone positions)",
        "",
        "Bone positions: centre, top and bottom edges, top and bottom corners, IM1 / IM2 notch roots, US2 corner relief, "
        "between the rails, over the rail, at a clip, and the four points of each layout furthest from any support "
        "(bay centres). Walking 1.6 g, factored 2.0 g × 1.5 (HA-LS-1 rev B C5).",
        "",
        "| option | frame +g | sheet g | clips + tubes g | total g | frame SF | frame fat | rib SF | rib fat | air walk | air fact | air lean | sheet MPa walk / fact | skin kPa | cost $ | pass (barrier rule) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        fr = r["frame"]
        lines.append(
            f"| {r['short']} | {r['frame_delta_g']:+.0f} | {r['sheet_g']:.0f} | {r['clips_g'] + r['tubes_g']:.0f} | "
            f"**{r['total_g']:.0f}** | {fr['sf_min']:.2f} | {fr['sf_fatigue']:.2f} | {_f(r['rib_sf_fact'])} | "
            f"{_f(r['rib_sf_fatigue'])} | {r['clear_walk_min']:.1f} | {r['clear_fact_min']:.1f} | "
            f"{r['clear_fact_lean_min']:.1f} | {r['s_walk_max']:.0f} / {r['s_fact_max']:.0f} | {r['skin_peak_kpa']:.1f} | "
            f"{r['cost']['total']:.0f} | {'yes' if r['passes'] else 'no: ' + ', '.join(r['fails'])} |")
    lines += [
        "",
        "Frame SF and fatigue are the whole-frame minimum over all HA-LS-1 rev B cases and the three torsos (2 mm). "
        "Rib SF is the cross members under the factored bone + meat (PAHT 0.8 knockdown; carbon tube hot/wet and impact "
        "knockdowns on compression). Airs are the minimum gap from the lowest part (sheet, rib bottom or tube) to the skin. "
        "Strict-rule sheet SFs are in the JSON (`sf_sheet_yield`, `sf_sheet_fatigue`); every HDPE row is below 1 there. "
        "This table is the named + bay-centre run (15 positions); the recommendation quotes the chosen layout's "
        "33-position run (named + bays + a 48 mm grid), which is a little harsher.",
        "",
        "What the families do:",
        "",
        "- **Printed PAHT ribs are too soft.** A 7 × 14 mm rib in hot/wet PAHT (E 2.3 GPa) spanning branch to branch "
        "bends 9–11 mm under the factored bone. Its depth plus that bend is what eats the air to the skin. Deeper ribs "
        "hit the torso bulge on the lean case; wider ribs cost ~50 g each.",
        "- **X ribs** span longer and shed the bone into the branches at mid-height, where the branches are softest.",
        "- **A coarse grid** adds a spine rib in the gutter: it blocks the air path and adds mass for little deflection.",
        "- **Carbon cross stays** are far stiffer per gram than printed ribs (E 75 GPa against 2.3 GPa hot/wet). "
        "A 12/10 mm roll-wrapped stay weighs about 11 g and bends 2–4 mm under the factored bone. This is the Seek "
        "Outside answer, in carbon instead of 7075. Two or four stays leave 100–160 mm bays that the meat pressure "
        "yields; six at about 50 mm pitch do not.",
        "- **12 mm stays need 6 mm more room on a leaning torso.** With the sheet on the stay crowns, the stays' "
        "underside bottoms on the lean case by about 3 mm in the gutter. Raising the sheet 6 mm on the clip saddles "
        "(d6L) clears it. Branch and bar lands then do not touch the sheet and are left off.",
        "- **Edges only (e)** is light, but the sheet spans the 160 mm bay between the branches and bottoms on the lean torso.",
        "",
        "## 3. Frame re-check, chosen layout vs today (2 mm, worst torso)",
        "",
        "| case | today | chosen |",
        "|---|---:|---:|",
    ]
    for cs in CASES:
        lines.append(f"| {cs} | {base['cases'].get(cs, float('nan')):.2f} | {frc['cases'].get(cs, float('nan')):.2f} |")
    lines += [
        f"| fatigue | {base['sf_fatigue']:.2f} | {frc['sf_fatigue']:.2f} |",
        f"| creep-rupture | {base['sf_creep']:.2f} | {frc['sf_creep']:.2f} |",
        f"| torsion vs tube frame | {base['torsion_rel']:.2f} | {frc['torsion_rel']:.2f} |",
        f"| printed body g (2 mm raster) | {base['body_g']:.0f} | {frc['body_g']:.0f} |",
        "",
        "The ribs, lands and sockets are not on the main load paths of the frame cases. They change the case SFs "
        "very little and add a little torsional stiffness.",
        "",
        "## 4. Sheet material on the chosen layout",
        "",
        "| sheet | sheet g | MPa walk / fact (FI for G10) | strict SF yield / fatigue | air lean mm | Neuber strain | passes barrier rule | passes strict rule |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for k in ("hdpe15", "hdpe10", "uhmw15", "g10_10"):
        r = fin.get(k)
        if not r:
            continue
        lines.append(f"| {r['sheet_name']} | {r['sheet_g']:.0f} | {r['s_walk_max']:.2f} / {r['s_fact_max']:.2f} | "
                     f"{r['sf_sheet_yield']:.2f} / {r['sf_sheet_fatigue']:.2f} | {r['clear_fact_lean_min']:.1f} | "
                     f"{_f(r.get('strain_fact_neuber'), 3)} | {_yn(r['passes_barrier'])} | {_yn(r['passes_strict'])} |")
    lines += [
        "",
        f"The chosen HDPE row was run on the named, bay-centre and a {int(48)} mm grid of bone positions "
        f"({h15['n_positions']} in all). G10 is a brittle laminate, so it is held to the strict first-ply rule, and a "
        "1.0 mm sheet fails it by a wide margin under the bone. It also weighs more than 1.5 mm HDPE. UHMWPE is softer "
        "and weaker than HDPE for the same mass. 1.0 mm HDPE saves grams and dents deeper.",
        "",
        "## 5. Rib-layer topology optimisation",
        "",
        f"`spreader_layout.rib_simp`: a PAHT rib layer 14 mm deep under the HDPE sheet, {ctx['simp']['volfrac'] * 100:.0f} % "
        f"volume ({ctx['simp']['mass_g']:.0f} g if printed as a smeared web), SIMP p = 3 with a 10 mm filter, minimum "
        "compliance under the factored meat pressure plus a 48 mm grid of factored bone ends, on the real crowns, branch "
        "lands and bar. The material goes into the bottom bay below the branches (z 130–200), where the meat pressure peaks and nothing else supports the sheet, with thin ties up to the branches. It is not symmetric (no symmetry constraint, 30 iterations), so it is used to place members, not printed: the chosen layout puts two of its six stays there (z 124, 165), both at 14/12 mm. A printed web at that volume is heavier than carbon stays for the same stiffness.",
        "",
        "## 6. Airflow, printing, cost, washing",
        "",
        "| option | gutter crossings | worst blockage of the 20 mm air gap | rib length on tree supports mm |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(f"| {r['short']} | {r['air']['crossings']} | {r['air']['worst_block'] * 100:.0f} % | "
                     f"{r['print']['supported_rib_mm']:.0f} |")
    lines += [
        "",
        "- Air: the air path stays the gutter between the rails under the open mesh. Horizontal members across the gutter "
        "choke the chimney flow up the back. Round 12 mm tubes block less than flat 14 mm ribs and leave the gutter fully "
        "open when they are out. The sheet stays solid: it is the bag-side blood and sweat barrier.",
        "- Printing (H2S, wearer face down, split at z 234): the sockets are open-top cups (snap-in, about 220° wrap) "
        "grown on the branches and stays, printed with the frame; their undersides take tree supports like the existing "
        "branches (README: only where the slicer flags bridges > 15 mm). The segment footprints do not change. Printed "
        "ribs and lands (options a–c, e) would add 2–3 h of print and long supported spans.",
        f"- Cost: sheet stock ${c['sheet']:.0f}, cutting ${c['cut']:.0f}, extra filament ${c['filament']:.0f}, carbon "
        f"tube ${c['tubes']:.0f}, clips ${c['clips']:.0f}: about **${c['total']:.0f}**.",
        "- Washing: the sheet lifts out after the 6 clips; the carbon stays pull out of their sockets; the frame hoses clean.",
        "",
        "## 7. Mass budget, before and after",
        "",
        "| item | today (2.0 mm QI) | sandwich v2 | thin sheet on this layout |",
        "|---|---:|---:|---:|",
        f"| sheet | 193 | 99 | {m['sheet_g']:.0f} |",
        f"| fasteners (M4 / clips, pucks, doublers, seal) | 10 | 34 | {m['clips_g']:.0f} |",
        f"| bonded edge tubes / removable carbon stays | 0 | 21 | {m['tubes_g']:.0f} |",
        f"| added frame (sockets) | 0 | 0 | {m['frame_delta_g']:.0f} |",
        f"| **total** | **203** | **154** | **{m['total_g']:.0f}** |",
        "",
        "Mass reductions: 1.0 mm HDPE saves " + f"{h15['sheet_g'] - fin['hdpe10']['sheet_g']:.0f}" + " g "
        + ("and passes the barrier rule here (table 4; T8 at 1.0 mm before using it)." if fin['hdpe10']['passes_barrier']
           else "but fails the barrier rule here (table 4).") +
        " 10/8 mm stays would save about 20 g but drop the stay SF below 1 under a bone on mid-span. "
        "Trimming the sheet's overhang outboard of the stay crowns saves about 6 g.",
        "",
        "## 8. Files",
        "",
        f"- Frame print files with the six stay sockets: `{ctx['files']['assembled']}`, "
        + ", ".join(f"`{f}`" for s in ctx["files"].get("segments", {}).values() for f in s["files"]),
        f"- Sheet cut file (DXF, mm; CUT, MARK = support lines, TEXT): `{ctx['files']['dxf']}`",
        f"- Sheet drawing, 1:1 A3: `{ctx['files']['drawing']}`",
        f"- viz3d back-system mesh (sheet + carbon stays): `{ctx['files']['barrier']}`",
        "- Results: `designs/pack_5200/analysis/spreader_layout_results.json`",
        "",
        "## 9. Sources added",
        "",
        "- HDPE fatigue: Djebli et al., *Uniaxial Fatigue of HDPE-100 Pipe*, ETASR 4(2):600–604 (2014), R = 0, 2 Hz, "
        "Basquin Smax = 32.46 N^−0.067 MPa (Ps 50 %) → 15.0 MPa at 1e5 cycles "
        "([ETASR](https://www.etasr.com/index.php/ETASR/article/view/422)). Fetched.",
        "- HDPE yield vs temperature: PE-100 yield falls about linearly from 32 to 9 MPa between −10 and 70 °C "
        "([KFUPM](https://pure.kfupm.edu.sa/en/publications/effect-of-temperature-on-tensile-properties-of-hdpe-pipe-material/)) "
        "*(reported, search summary)*; the 0.78 factor at 40 °C is interpolated from it. Amjadi & Fatemi, Polymers "
        "12:1857 (2020) ([PMC7564066](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7564066/)) reports the same linear trend.",
        "- Leaders' sheets and cross stays: `docs/research/spreader_research.md` §1 and §8 (Seek Outside fetched).",
        "",
        "## Screenshots",
        "",
    ]
    lines += [f"- `{s}`" for s in ctx["screens"]]
    lines += [
        "",
        "## Assumptions",
        "",
        "- ASSUMPTION: bone end 20 % of 68 kg on a 22 mm patch (HA-LS-1), part of the meat, not added to it.",
        "- ASSUMPTION: a thin thermoplastic barrier may yield locally under a bone end (barrier rule above); the owner "
        "decides, and T8 checks it.",
        "- ASSUMPTION: HDPE yield and fatigue at 40 °C = 0.78 × room temperature; UHMWPE fatigue scales with its yield.",
        "- ASSUMPTION: Neuber's rule on an elastic-perfectly plastic curve for the local strain at the patch rim.",
        "- ASSUMPTION: the sheet is held in-plane only at the 6 clip stations; it slides freely on lands, ribs and tubes.",
        "- ASSUMPTION: below the upper lumbar strut line the back rests on the lumbar pan (skin reference = strut wearer "
        "face), blended to the free gutter skin over 60 mm of height.",
        "- ASSUMPTION: the meat-only sheet check uses the 99th-percentile stress, as the frame FEA does, so single "
        "contact-edge elements at the clip saddles and stay ends do not govern.",
        "- ASSUMPTION: printed ribs and lands top out 0.3 mm below the sheet plane (print tolerance); the sheet plane is "
        f"the stay-crown plane, y = sleeve axis + {L.R_PLANE:.1f} mm.",
        "- ASSUMPTION: rib, land and branch stiffness at PAHT hot/wet (0.6 E); ribs fused where they cross a branch.",
        "- ASSUMPTION: carbon stays are roll-wrapped 14/12 and 12/10 mm (record E 75 GPa, compression 450 MPa × 0.8 × 0.65), "
        "pinned in their sockets (no end moment).",
        "- ASSUMPTION: the bone reaction reaches the stays by the lever rule between the stays (skin-pressure input).",
        "- ASSUMPTION: the air gap in the gutter is 20 mm at rest for the blockage estimate.",
        "- ASSUMPTION: sheet stock bought at 2× the part mass, $6/kg (record), $8 to CNC-cut one part; clips $12.",
        "- Torso radius 230 mm (150 mm lean), soft tissue 60 kPa over 25 mm, 3 mm spacer mesh: as `spreader.md`.",
        "",
    ]
    path = ANALYSIS / "spreader_layout.md"
    path.write_text("\n".join(lines))
    return path


def ctx_g(which: str) -> str:
    return "203" if which == "cur" else "154"
