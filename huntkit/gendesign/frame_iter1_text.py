"""Prose of the BL-061 record (frame_iter1.md). Every number is read from the result dict (frame_iter1.json)."""
from __future__ import annotations

from . import frame_iter1 as F


def _lb(g):
    return f"{g / 453.592:.2f} lb"


def _oz(g):
    return f"{g / 28.3495:.1f} oz"


def narrative(res: dict, part: str) -> list:
    cs = res["concepts"]
    h = cs["h1"]
    rec = res.get("recommended", "cflite")
    r = cs.get(rec, h)
    hs, hc = h["static_cinch"], h["cinch_cycled"]
    rs, rc = r["static_cinch"], r["cinch_cycled"]
    fl = res["frame_line_h1_g"]
    if part == "summary":
        return [
            "## Summary",
            "",
            f"- **Recommendation: {rec.upper()}** ({r['label'].split(':', 1)[-1].strip()}). Frame line **{r['frame_line_g']:.0f} g "
            f"({_lb(r['frame_line_g'])})** against H1's {fl:.0f} g: **{r['mass']['delta_g']:+.0f} g ({_oz(r['mass']['delta_g'])})**. "
            f"Every HA-LS-1 rev C body row is at or above H1's: strength {rs['strength']:.2f} (H1 {hs['strength']:.2f}), "
            f"fatigue {rs['fatigue']:.2f} ({hs['fatigue']:.2f}), creep {rs['creep']:.2f} ({hs['creep']:.2f}), "
            f"**buckling {rs['buckling_record']:.2f} ({hs['buckling_record']:.2f})** on the record rule and "
            f"{rs['buckling_section']:.2f} ({hs['buckling_section']:.2f}) on the stricter section rule, and "
            f"**cinch-cycled fatigue {rc['fatigue']:.2f} ({hc['fatigue']:.2f})**: both rubric bonuses are met "
            "(buckling >= 1.15, cinch-cycled >= 1.0, which lifts the R1 hold). Carbon tube strength / fatigue "
            f"{rs.get('tube_strength', 0):.2f} / {rs.get('tube_fatigue', 0):.2f}, tube-to-node bonds min {rs.get('bond_min', 0):.2f}.",
            f"- **The mass target is not met.** The ticket aimed at >= 150 g off the frame; the best concept that keeps every "
            f"margin saves {-r['mass']['delta_g']:.0f} g. Section 3 shows where the rest of the mass sits: the three printed "
            "parts still carry every bag interface (lugs, fairleads, hinge eyes, hip boss with 8 inserts, pawl housing, "
            "spine channel), and on the 2 mm voxel grid a printed wall cannot go below 4 mm.",
            "- **A 900 g frame line (the orchestrator's bold target) cannot be reached without losing margin** while the "
            "crown, the torso adjustment and the bag interfaces stay. Section 5.2 gives the arithmetic.",
            f"- **Found on H1 (not fixed, it is released):** with each member's real section (I_min of the cut) instead of "
            f"the record rule's solid-round equivalent, H1's member buckling is **{hs['buckling_section']:.2f}**, not "
            f"{hs['buckling_record']:.2f} (upper branch R: a 16 x 12 mm flat section has 81 % of the round's I). Only the "
            "record rule's K = 1 (pinned ends; the fused ends are stiffer) covers it. The printed-frame side-squeeze test "
            "in h1_buckling's EULER_RULE assumption, or a linear eigenvalue run, settles it. It is one more reason to "
            "adopt box members whatever concept is chosen.",
            "- Side task: the T1 US1 ROOT gauge is now record only, and the second US1 gauge was re-run on the current "
            "STL and md5-locked (section 7).",
        ]
    if part == "concepts":
        g, b, cf, cb = (cs.get(k) for k in ("graded", "box", "cfstay", "cfbox"))
        out = ["### What each concept is, and what it showed", ""]
        if g:
            out.append(f"- **C GRADED** (slicer only: released STL, 4 mm wall shell, 15 % gyroid core where H1's "
                       f"utilisation is below {F.U_CUT}, 100 % at every hard point): {g['mass']['delta_g']:+.0f} g, and "
                       f"weaker everywhere: strength {g['static_cinch']['strength']:.2f}, buckling "
                       f"{g['static_cinch']['buckling_record']:.2f} (below R1), cinch-cycled "
                       f"{g['cinch_cycled']['fatigue']:.2f}. The core carries part of the bending in the upper bar "
                       "and the members; taking it out costs more margin than mass. Rejected.")
        if b:
            out.append(f"- **A BOX** (branches and mid bar grown 2 mm and made closed boxes; low-utilisation thick "
                       f"zones hollowed into ribbed cavities with a 2 mm diaphragm every {F.DIAPHRAGM_PITCH:.0f} mm; the "
                       f"cinch-cycled hot spot grown 2 mm): {b['mass']['delta_g']:+.0f} g. Buckling "
                       f"{b['static_cinch']['buckling_record']:.2f} and cinch-cycled {b['cinch_cycled']['fatigue']:.2f} "
                       f"improve, but strength falls to {b['static_cinch']['strength']:.2f} (hipbelt-off abuse, upper bar "
                       "/ pawl housing: a cavity there). Not lighter; the box members are the useful part.")
        if cf:
            out.append(f"- **B CF-STAY** (two 22 x 18 roll-wrapped carbon tubes as the stays, crown legs sliding inside "
                       "as today; printed P1 lower node, P2 branch X with three sleeves, P3 top node, slid on and bonded; "
                       f"the z 234 bolted split deleted): {cf['mass']['delta_g']:+.0f} g. Fatigue jumps to "
                       f"{cf['static_cinch']['fatigue']:.2f} and cinch-cycled to {cf['cinch_cycled']['fatigue']:.2f} "
                       "(the tubes take the stay bending off the printed roots), strength holds "
                       f"({cf['static_cinch']['strength']:.2f}), but member buckling falls to "
                       f"{cf['static_cinch']['buckling_record']:.2f}: the stiffer stays push more of the side-hill racking "
                       "through the branches. Fails R1 as is.")
        if cb:
            out.append(f"- **D CF-BOX** (CF-STAY + A's box members, hot-spot growth and cavities sized on H1's "
                       f"utilisation): {cb['mass']['delta_g']:+.0f} g, buckling {cb['static_cinch']['buckling_record']:.2f}, "
                       f"but strength {cb['static_cinch']['strength']:.2f} (the same upper-bar cavity as BOX).")
        out.append("- CF-STAY and CF-BOX were solved before the full bond sleeve was added (their FE has a few "
                   "windows in the printed sleeve, slightly conservative); their masses are booked with it.")
        out.append(f"- **E CF-LITE** (CF-STAY + box members + every printed stay voxel outside the 14 mm sleeve removed "
                   "in P1 and P2 where CF-STAY used it below 0.4, + cavities where CF-STAY's own utilisation is below "
                   f"{F.CFLITE_UCUT}, none in the top node): the concept that keeps every margin. Its first version "
                   "(also trimming P3 and deepening the members in y only) failed: strength 1.50 at the top bushing and "
                   "upper branch R buckling 0.91 (record `outputs/iter1_frame/check_cflite_v1.json`); both were "
                   "reverted. Its second version left windows in the printed sleeve where H1's lower legs were narrower "
                   "than 28 mm; the full 3 mm sleeve over every bonded length is in the version reported here "
                   "(+25 g).")
        return out
    if part == "method":
        ts = cs.get("cflite", {}).get("info", {}).get("tube") or {}
        return [
            "",
            "- **Geometry.** Every concept starts from the released print `print/frame_h1/h1_assembled.stl` "
            f"(md5 {F.STL_MD5}), re-rastered on the H1 2 mm grid (`bl058_frame.body_stl`). Interfaces are not moved: "
            "hinge eyes, US1 / US2 lanes and clevises, the 12 fairleads, the crown bores (18 mm), the hip boss and its 8 "
            "insert pilots, the pawl housing and the spine channel are protected voxels in every concept "
            "(`frame_iter1.protected`, `hard_points`). The voxel envelope stops at y 16 and |x| 152; outside it (fairlead "
            "tops, US2 clevises) nothing changes.",
            "- **Check.** The BL-055 / BL-058 whole-body check, unchanged: 42 rev C sets x 3 crown kits on the "
            "fine_sm8, fine and beam bases plus the cinch-cycled fine_sm8.cyc basis, lane kit sets, real crown models, "
            "H1's FI99 layer rule (PAHT-CF 88 / 47 MPa x 0.8), fatigue 0.30 x at 1e5 x 1.6 g, creep 0.40, stays sanded "
            "(k 1.0416). **The H1 run reproduces bl058.json exactly** (strength 1.630, fatigue 1.249, creep 2.664, "
            "buckling 1.053, cinch-cycled 0.856), so the concept numbers are on the record's basis.",
            "- **Extensions** (`frame_iter1.check`): per-voxel stiffness weights (`h1_sleeve.solve_fields_w`); gyroid core "
            f"E x {F.W_GYROID:.4f}, its FI against the gyroid strength x {F.S_GYROID:.4f} (ASSUMPTION GYROID); carbon tube "
            f"voxels: a 1-voxel ring r 9-11 mm with weight {ts.get('weight', 0):.1f} that matches the tube's EI (EA "
            f"{ts.get('EA_ratio_vox_over_tube', 0):.2f} x, GJ {ts.get('GJ_ratio_vox_over_tube', 0):.1f} x the real tube: "
            "torsion is over-attracted, conservative for the tube and its bonds); tube stress = the voxel strain x 75 "
            "GPa; tube FI = max-stress with the knock-downs kept (Xt 650 x 0.8, Xc 450 x 0.8 x 0.65, S 90 x 0.8; "
            "p99 over the tube voxels outside the load patches; fatigue FI at 1.6 g <= 0.5); tube resultants (N, M, T) "
            "at bare cuts between the sleeves give each sleeve's transfer for the bond check (section 4). The z 234 "
            "joint check runs only where the split exists.",
            "- **Solver verification.** The FE path is the record's (tests in `tests/test_h1_*`, `test_frame_h1.py`). "
            "New closed-form tests (`tests/test_frame_iter1.py`): voxel section I of a rectangle and a box against "
            "b d^3 / 12, Euler P_cr, Volkersen limits, the bond and pin margins on a synthetic resultant record.",
        ]
    if part == "buckling":
        return [
            "Record rule (team A, used for every H1 record): member voxel area at the cut as a solid round, pinned-pinned "
            "K 1, E 3860 x 0.6 hot x 0.7 creep, margin = P_cr / (1.5 x factored compression). Section rule: the same "
            "but with the cut's real weighted I_min. On H1 the section rule is stricter (flat 16 x 12 and 14 x 12 mm "
            "members); on box members it credits the hollow section. The recommended concept passes both.",
        ]
    if part == "mass":
        return [
            "Masses: printed parts from the 2 mm raster at 1.06 g/cm3 (deltas against H1's raster applied to the 1069.32 g "
            "released STL, so the raster-to-STL difference cancels); tubes 22 x 18 at the record's 1550 kg/m3 (0.195 g/mm; "
            "a 22 x 19 listing implies 1.45 g/cm3, research section 3); MMA 0.98 g/cm3 at its bondline; Ti M4 x 30 bolts "
            "(ASSUMPTION BOLT-G 0.8 g head and nut); the z 234 joint hardware from frame_mass_h1.json. Everything else "
            "in the frame line (crown legs, top bar, spine tube, corner wraps, rack, pawl, guides, bushings, Ti hip "
            "mount, inserts, pins, US2 clevis hardware, torso-adjust webbing) is unchanged in every concept.",
            "",
            "**What besides the print each concept removes:** CF-STAY / CF-BOX / CF-LITE delete the z 234 split's 4 Ti "
            "M5 x 45, 4 nuts and 8 washers (28.0 g) and its two printed bolt bosses, and add 2 tubes, the bond and 4 Ti "
            "M4 fail-safe bolts. BOX and GRADED change the print only. No concept touches the crown, the rack / pawl or "
            "the pins (owner-frozen interfaces and lifters on the crown top bar).",
            "",
            f"Where {rec.upper()}'s printed mass is (raster): " + "; ".join(
                f"{k} {v:.0f} g" for k, v in r["mass"].get("parts_raster_g", {}).items())
            + ". P1 holds the lumbar X struts, the hip boss with 8 inserts, the US1 / US2 lug arms and clevis blocks, "
            "the hinge eyes, IM1 and the feet; P3 the upper bar, pawl housing, spine channel, crown bushing seats and "
            "IM3. Most thick zones are now 4 mm shells with ribs; the next grams need walls under 4 mm, which the 2 mm "
            "grid cannot represent (iteration 2: a 1 mm submodel of P1 and P3), or fewer printed features.",
        ]
    if part == "joints":
        return [
            "Rules (HA-LS-1 4): average shear >= 1 at the factored load; Volkersen elastic peak >= 1 at LIMIT load "
            "(limit cases; the ultimate cases C7 / C8 are judged on the average, the toughened MMA yields at the peak "
            "and redistributes); fatigue: 1.6 g static-carry average <= 0.3 x the dry allowable. Allowable 5.0 x 0.8 = "
            f"{F.BOND_PA_MPA * F.BOND_HOT_WET:.1f} MPa (ASSUMPTION BOND-PA: the printed polyamide side governs, "
            "published 3.7-5.0 MPa with interface failure). Shear modulus 300 MPa (ASSUMPTION MMA-G). P1 and P3 at a 0.8 mm "
            "bondline (glass beads, as the rev C crown corners); P1 bonded in two 40 mm bands and checked as if one band "
            "took it all. Bending goes in by bearing over the sleeve (p = 6 M / (d L^2) against 47 x 0.8 MPa). Fail-safe: "
            f"one Ti M4 cross bolt in P1 and in P3 carries the axial force and the torque alone at limit, bearing on the "
            f"tube's two 2 mm walls at {F.TUBE_BEARING_MPA:.0f} MPa (ASSUMPTION TUBE-BEARING).",
            "",
            "The tightest is the P3 Volkersen peak in side-hill torsion; in the hipbelt-off abuse case (ultimate) the "
            "P3 peak is below 1 as information (see the json `peak_ultimate_info`): that case is covered by the average and "
            "by the fail-safe bolt. The voxel tube over-attracts torsion by about 2.3 x, so all torsion-driven bond "
            "numbers are conservative. CF-STAY and CF-BOX were run before the torque column was added: their bond rows "
            "carry no torque (json `bond_torque_in_model`).",
        ]
    if part == "recommendation":
        return [
            "",
            "| rubric axis | H1 | " + " | ".join(n.upper() for n in cs if n != "h1") + " |",
            "|---|---|" + "---|" * (len(cs) - 1),
            "| 1 Strong (gate: every row >= H1's) | baseline | " + " | ".join(
                ("pass" if v["gate"]["at_least_as_strong"] else ("R1 only" if v["gate"]["R1_pass"] else "FAIL"))
                for n, v in cs.items() if n != "h1") + " |",
            "| bonus: buckling >= 1.15 / cinch-cycled >= 1.0 | 1.05 / 0.86 | " + " | ".join(
                f"{v['static_cinch']['buckling_record']:.2f} / {v['cinch_cycled']['fatigue']:.2f}"
                for n, v in cs.items() if n != "h1") + " |",
            f"| 2 Lighter (frame line) | {fl:.0f} g | " + " | ".join(
                f"{v['frame_line_g']:.0f} g ({v['mass']['delta_g']:+.0f})" for n, v in cs.items() if n != "h1") + " |",
            "| 3 Looks (frame surfaces intentional) | printed branch body | same | same, ribbed inside | carbon stays + "
            "printed knuckles | same | same |",
            f"| print time (est.) | {h['print_h_est']:.0f} h | " + " | ".join(
                f"{v['print_h_est']:.0f} h" for n, v in cs.items() if n != "h1") + " |",
            "",
            f"### 5.1 Recommendation: {rec.upper()}",
            "",
            f"It is the only concept that passes the strength gate against H1 on every row and is lighter "
            f"({r['mass']['delta_g']:+.0f} g). It also takes both bonuses: buckling {rs['buckling_record']:.2f} "
            f"(target 1.15) and cinch-cycled fatigue {rc['fatigue']:.2f} (target 1.0, lifts the R1 hold for MT-1). "
            "It reads as carbon stays with printed knuckles (the look the owner asked frame_light2 for on 2026-11-09), "
            "and it removes the z 234 bolted split, the part of H1 with the most hardware and two review cycles.",
            "",
            "**Build (beginner, home):** buy two 22 x 18 mm roll-wrapped tubes (1 m, cut to 514 mm with a fine hacksaw "
            "in a printed mitre jig, ends sealed with thin CA); print P1, P2, P3 flat on the H2S (each fits 340 x 320; "
            "no split, no joint bolts); scuff the tubes (120 grit) and the sleeve bores, flame-treat the PAHT-CF "
            "(as T6p), slide the parts on in order P1, P2, P3 in a printed alignment jig, MMA with 0.8 mm glass beads in "
            "P1 / P3, 0.5 mm in P2; drill the two fail-safe M4 holes through P1 / P3 using the printed part as the drill "
            f"guide. Room-temperature cure. Printing about {r['print_h_est']:.0f} h against H1's {h['print_h_est']:.0f} h "
            "(estimate, same rule), plus one evening of bonding in a jig; no z 234 bolt fitting.",
            "",
            "**Main risk:** the printed-PAHT-to-carbon bond at the P3 top node in torsion (Volkersen peak "
            f"{r.get('bonds', {}).get('P3 top node', {}).get('peak', {}).get('margin', float('nan')):.2f} in side-hill "
            "torsion, below 1 as information in the hipbelt-off abuse case), resting on an unpublished value "
            "(ASSUMPTION BOND-PA 4.0 MPa, published PA12 3.7-5.0 MPa).",
            "",
            "**Test that retires it: T6p-T (new)**: 3 coupons of a 120 mm tube offcut bonded into a printed P3-style "
            "sleeve (72 mm, 0.8 mm bondline, the build's prep), pulled axially to failure and 3 twisted to failure on "
            "the pull bench (kit A). Pass: mean axial >= 1.5 x and torque >= 1.5 x the largest limit transfer "
            "(frame_iter1.json bonds), lowest >= 1.25 x, cohesive or substrate failure; plus 1e5 cycles at the 1.6 g "
            "fatigue transfer on one coupon. Then T1 / T3 on the bonded frame as HA-LS-1 5.3.",
            "",
            "### 5.2 Why not 900 g",
            "",
            f"H1's frame line is {fl:.0f} g, of which {fl - 1069.3:.0f} g is outside the print (crown, rack / pawl, "
            "bushings, Ti hip mount, inserts, pins, clevis hardware, torso-adjust webbing). Holding that, 900 g leaves "
            f"about {900 - (fl - 1069.3):.0f} g for the print-plus-tubes; CF-LITE's print-plus-tubes is "
            f"{r['mass']['frame_print_g']:.0f} g. The only architecture in the repo that gets there is the v2 ladder "
            "(frame_light2 TENDON: printed nodes 238 g + tubes 103 g + wraps 40 g + bonds 22 g + pan 123 g, about "
            "526 g + 318 g = about 844 g with H1's crown and hardware), but its rev C minimum was strength 1.04 / "
            "fatigue 1.07 on the beam model, against H1's 1.63 / 1.25: it loses margin, and it lacks H1's lug arms, "
            "clevises and spine channel. So **no 900 g concept is offered as passing**. Iteration 2 could FE a "
            "TENDON-class ladder with H1's interfaces, sized to H1's margins (estimate 900-1000 g).",
        ]
    if part == "assumptions":
        return [
            "",
            "- ASSUMPTION GYROID: E* = rho^2, strength 0.3 rho^1.5 for 15 % PAHT-CF gyroid (Gibson-Ashby; Bean 2022 says "
            "the power law fits poorly). Only GRADED uses it. Settled by GY-1 (shell + core beam bend and compression).",
            "- ASSUMPTION BOX-ENVELOPE: members grown 2 mm stay inside the stays' y span (-23..9) and clear of the "
            "spreader and back rails. Settled by a fit check of the re-exported print against the spreader / rail CAD "
            "(spreader clips, CLIP_Z) before release.",
            "- ASSUMPTION CAVITY-PRINT: closed cavities with 2 mm diaphragms every 40 mm print with bridged roofs on "
            "the H2S (cavity roofs drawn as 45 deg diamonds in the CAD). Settled by a sectioned print of one P1 strut.",
            "- ASSUMPTION TUBE: 22 x 18 roll-wrapped tube to the record (E 75 GPa, 650 / 450 MPa, ESTIMATE); ID 18.0 "
            "+/- 0.1. Settled by a 3-point bend of one offcut per batch and a bore gauge (record note).",
            "- ASSUMPTION TUBE-VOXEL: the isotropic voxel ring matched on EI (EA 0.95 x, GJ 2.3 x). Settled by the "
            "T1 / T3 deflection readings against the model.",
            "- ASSUMPTION BOND-PA (4.0 MPa design), MMA-G (300 MPa), P1-BANDS (one band may take all), SLEEVE-BEARING "
            "(47 x 0.8 MPa), TUBE-BEARING (250 MPa pin bearing), BOLT-G. Settled by T6p-T (bond, torsion) and T6b "
            "(M4 pin bearing in a tube offcut).",
            "- ASSUMPTION CLIPS: the spreader clips and the hinge-eye / fairlead geometry re-seat on the 22 mm tube or "
            "on the printed sleeves unchanged (the fairleads stay on printed parts at their current positions).",
            "- The H1 record's own assumptions (SUB-BC, EULER_RULE, PAHT_FAT, CINCH_STATIC, MESH, SAND-K) carry over.",
        ]
    return []
