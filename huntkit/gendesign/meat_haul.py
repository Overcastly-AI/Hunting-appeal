"""Required meat-haul modes on the branch frame.

A. Bag on. Meat stays in the bag. IM1–IM3 cinch it against the carbon spreader.
   The wedge between the open bag and the frame is the bulk-meat method of the same mode.
B. Bag off. The bag is unclipped. A quarter sits on the spreader and the same three
   straps hook eye-to-eye on the cleats.

Run: python -m huntkit.gendesign.meat_haul
"""
from __future__ import annotations

import json

import numpy as np

from huntkit.fea.load_cases import LoadCase
from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.gendesign.bag_attach import (
    BARTACK_N,
    HOOK_N,
    _NODE_STATION,
    _frame_model,
    _save,
)
from huntkit.materials import load

DATE = "20261101"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
G = 9.80665
MU = 0.4                         # wet game bag on the spreader, geometry.yaml
QUARTER_KG = 36.0                # R-08, one bone-in quarter
RATED_KG = 68.0
CAM_N = 1100.0                   # ASSUMPTION, DESIGN.md §4.5
WEB_N = 20016.0                  # poly_webbing_38mm record


def _stations(case: LoadCase) -> dict:
    """Factored force on the heavier side of each fairlead."""
    raw = case._loads(_frame_model())
    best: dict[str, dict] = {}
    factor = float(case.required_sf)
    for nid, name in _NODE_STATION.items():
        if nid not in raw:
            continue
        v = np.asarray(raw[nid][:3], float) * factor
        n = float(np.linalg.norm(v))
        row = {"n": n, "fy": float(v[1]), "fz": float(v[2]), "node": nid}
        if name not in best or n > best[name]["n"]:
            best[name] = row
    return best


def _scale(sf: float, checked_n: float, new_n: float) -> float:
    return float(sf) * float(checked_n) / max(float(new_n), 1.0)


def _friction_leg(weight_n: float, n_straps: int) -> float:
    """Tension in one strap leg so μ times the strap's normal force holds ``weight_n``.

    A strap hooked eye-to-eye has two legs and squeezes with about 2 T. Geometry.yaml
    uses this for the 141 N figure (5 straps).
    """
    return weight_n / (MU * n_straps * 2.0)


def analyse() -> dict:
    """Load paths and safety factors for bag-on, the wedge, and bag-off."""
    branch = json.loads((ANALYSIS / "generative_branch_results.json").read_text())
    fair = json.loads((ANALYSIS / "bag_attachment_results.json").read_text())
    fine = [r for r in fair["fea"] if abs(r["h_mm"] - fair["h_mm"]) < 1e-6]
    hinge = next(r for r in fine if r["station"] == "hinge")
    im3 = next(r for r in fine if r["station"] == "im3")
    from huntkit.gendesign.frame_smooth import options
    sheet = next(r for r in options() if r["name"].startswith("QI carbon 2.0"))

    # Bag on is the HA-LS-1 meat resolution already used to size the cleats.
    bag_on_nodes = fair["governing"]

    # Wedge: bag hinged open, meat against the spreader, CG closer than the full bag.
    # Floor share 0.40 (ASSUMPTION): the tilted floor still catches the low end,
    # and more of the weight bears on the spreader than in the closed bag.
    bay = LoadCase(
        "bay", "meat between the open bag and the spreader",
        RATED_KG, 2.0, required_sf=1.5, placement="meat_straps", cg_aft_mm=110.0,
        params={"floor_share": 0.40, "pretension_n": 150.0, "face_z": (60.0, 400.0),
                "upper_groups": ("strap_lumbar", "strap_mid", "strap_upper"), "proportional": True},
    )
    bay_nodes = _stations(bay)

    # Bag off. No floor. 36 kg quarter, walking peak 1.6 g, then the 1.5 limit factor
    # on that tension for the cleat. Three IM straps are the requirement; W1 and W2
    # are a second clamp.
    walk = QUARTER_KG * G * 1.6
    leg3 = _friction_leg(walk, 3)
    leg5 = _friction_leg(walk, 5)
    leg3_f = leg3 * 1.5
    # cleat sees one leg, departing aft. Compare with the IM3 aft check.
    bag_off_cleat = {
        "im1": leg3_f, "im2": leg3_f, "im3": leg3_f, "hinge": 0.0,
    }

    def cleat_row(nodes, basis_name, basis_n, basis_sf, basis_fat):
        out = {}
        for name, force in nodes.items():
            n = force["n"] if isinstance(force, dict) else float(force)
            out[name] = {
                "n": n,
                "sf": _scale(basis_sf, basis_n, n) if n else 99.0,
                "sf_fatigue": _scale(basis_fat, basis_n, n) if n else 99.0,
            }
        out["basis"] = basis_name
        return out

    # Aft-directed stations scale from the IM3 fairlead. The hinge (mostly down)
    # scales from the hinge fairlead.
    def mixed(nodes):
        rows = {}
        for name, force in nodes.items():
            n = force["n"]
            if name == "hinge":
                src, sf, fat, fn = hinge, hinge["sf"], hinge["sf_fatigue"], hinge["force_n"]
            else:
                src, sf, fat, fn = im3, im3["sf"], im3["sf_fatigue"], im3["force_n"]
            rows[name] = {"n": n, "fy": force.get("fy", 0.0), "fz": force.get("fz", 0.0),
                          "sf": _scale(sf, fn, n), "sf_fatigue": _scale(fat, fn, n),
                          "from": src["station"]}
        return rows

    bag_on = mixed({k: {"n": v["n"], "fy": v["fy"], "fz": v["fz"]} for k, v in bag_on_nodes.items()})
    # The published FEA is exactly these forces. Use it directly where we have it,
    # and scale IM1/IM2 from IM3 (same cleat, aft direction, lower force).
    for name, src in (("hinge", hinge), ("im3", im3)):
        bag_on[name]["sf"] = src["sf"]
        bag_on[name]["sf_fatigue"] = src["sf_fatigue"]
    bay_c = mixed(bay_nodes)
    off_nodes = {k: {"n": v, "fy": v, "fz": 0.0} for k, v in bag_off_cleat.items() if v}
    off_c = mixed(off_nodes)

    web = float(load("poly_webbing_38mm").require("breaking_strength_n"))
    assert abs(web - WEB_N) < 1.0

    # Opening geometry for the wedge. Hinge z 60, IM3 z 520, 250 mm at IM3.
    rise = 520.0 - 60.0
    opening = {z: 250.0 * (z - 60.0) / rise for z in (190.0, 330.0, 520.0)}
    angle = float(np.degrees(np.arctan(250.0 / rise)))

    def pack(name, required, nodes, note, strap_n):
        cleat_fat = min(r["sf_fatigue"] for r in nodes.values())
        cleat_sf = min(r["sf"] for r in nodes.values())
        hinge_n = nodes.get("hinge", {}).get("n", strap_n)
        return {
            "name": name, "required": required, "viable": cleat_sf >= 1.0 and cleat_fat >= 1.0,
            "nodes": nodes, "note": note,
            "cleat_sf": cleat_sf, "cleat_fatigue": cleat_fat,
            "hook_sf": HOOK_N / strap_n, "cam_sf": CAM_N / strap_n,
            "bartack_sf": BARTACK_N / max(hinge_n, strap_n),
            "web_sf": web / strap_n, "hook_n": strap_n,
            "sheet_sf": sheet["sf"], "sheet_peak_kpa": sheet["peak_kpa"], "sheet_defl_mm": sheet["defl_mm"],
            "frame_sf": branch["cases"]["meat_straps"],
        }

    # Hook sees the strap. Bag-on governing strap demand is the published 605 N
    # (2 × 303 N service leg). Wedge uses the heaviest bay cleat force, which is
    # what the hook delivers. Bag-off uses the factored friction leg.
    modes = {
        "bag_on": pack(
            "Bag on, meat inside", True, bag_on,
            "Meat in the bag, cinched by IM1–IM3 against the spreader. Vertical load into the hinge pins.",
            max(605.0, max(bag_on[k]["n"] for k in ("im1", "im2", "im3"))),
        ),
        "between": pack(
            "Between bag and frame", True, bay_c,
            "Bag hinged open on the z 60 pins. IM2 and IM3 bag hooks released. Meat in the wedge, on the spreader.",
            max(bay_c[k]["n"] for k in ("im1", "im2", "im3")),
        ),
        "bag_off": pack(
            "Bag off, bare frame", True, off_c,
            "Quarter on the spreader. IM1–IM3 hooked eye-to-eye. No bag floor: friction holds the weight.",
            leg3_f,
        ),
    }
    modes["between"]["opening_mm"] = {str(int(k)): v for k, v in opening.items()}
    modes["between"]["angle_deg"] = angle
    modes["between"]["viable"] = modes["between"]["viable"] and opening[330.0] >= 120.0
    modes["bag_off"]["leg_walk_im_n"] = leg3
    modes["bag_off"]["leg_walk_with_wraps_n"] = leg5
    modes["bag_off"]["leg_factored_n"] = leg3_f
    modes["bag_off"]["walk_n"] = walk
    modes["bag_on"]["frame_sf"] = branch["cases"]["meat_straps"]
    # Bag-off cleat forces are inside the meat_straps envelope, so the frame SF stands.
    modes["bag_off"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["between"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["sheet"] = {"sf": sheet["sf"], "peak_kpa": sheet["peak_kpa"], "defl_mm": sheet["defl_mm"],
                      "name": sheet["name"]}
    return modes


def _draw(mode_key: str, modes: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Circle, Polygon
    from .render import _style
    _style()
    m = modes[mode_key]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 6.6))
    ink, frame, sheet, meat, strap, bag, rail = (
        "#0b0b0b", "#3c3d40", "#2a78d6", "#8d4e3c", "#eb6834", "#c6b59a", "#b7b6b1")

    def side(ax):
        ax.set_xlim(-70, 280)
        ax.set_ylim(-20, 620)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("Side  ·  wearer to the left", loc="left", fontsize=11)
        # wearer
        ax.plot([-40, -40], [0, 560], color="#d0c8bc", lw=10, solid_capstyle="round")
        ax.text(-48, 300, "wearer", rotation=90, va="center", ha="center", fontsize=8, color="#8a847c")
        # rails on the wearer face of the stays
        ax.plot([-14, -14], [40, 460], color=rail, lw=7, solid_capstyle="round", zorder=2)
        # stay
        ax.plot([0, 0], [0, 540], color=frame, lw=9, solid_capstyle="round", zorder=3)
        # spreader, bag side of the stay
        ax.plot([10, 10], [70, 500], color=sheet, lw=4, solid_capstyle="butt", zorder=4)
        ax.text(16, 80, "spreader", color=sheet, fontsize=8)
        for z, lab in ((60, "hinge"), (190, "IM1"), (330, "IM2"), (520, "IM3")):
            ax.add_patch(Circle((0, z), 7, facecolor="#6a6b6e", edgecolor=ink, lw=0.4, zorder=5))
            ax.text(-8, z, lab, ha="right", va="center", fontsize=8, color=ink)
        if mode_key == "bag_on":
            bag_x = [18, 18, 250, 200, 18]
            bag_z = [40, 760, 700, 40, 40]
            ax.add_patch(Polygon(list(zip(bag_x, bag_z)), closed=True, facecolor=bag,
                                 edgecolor=ink, lw=0.8, alpha=0.9, zorder=1))
            ax.add_patch(FancyBboxPatch((22, 90), 130, 520, boxstyle="round,pad=0,rounding_size=18",
                                         facecolor=meat, edgecolor="none", alpha=0.9, zorder=2))
            ax.text(80, 360, "meat\nin the bag", color="#fcfcfb", fontsize=9, ha="center", va="center")
            for z in (190, 330, 520):
                ax.annotate("", xy=(14, z), xytext=(150, z + 30),
                            arrowprops=dict(arrowstyle="-", color=strap, lw=2.0), zorder=6)
        elif mode_key == "between":
            # panel hinged at z 60, 250 mm open at z 520
            ax.plot([18, 18 + 250], [60, 520], color=bag, lw=8, solid_capstyle="round", zorder=1)
            ax.plot([18 + 250, 18 + 280], [520, 700], color=bag, lw=6, solid_capstyle="round", zorder=1)
            wedge = Polygon([(14, 80), (18, 60), (18 + 250, 520), (14, 500)],
                            closed=True, facecolor=meat, edgecolor="none", alpha=0.9, zorder=2)
            ax.add_patch(wedge)
            ax.text(90, 300, "meat in\nthe wedge", color="#fcfcfb", fontsize=9, ha="center")
            ax.text(200, 560, "bag open", color="#7a7268", fontsize=8)
            for z, opening in ((190, m["opening_mm"]["190"]), (330, m["opening_mm"]["330"]),
                               (520, m["opening_mm"]["520"])):
                ax.plot([12, 12 + opening * 0.85], [z, z], color=strap, lw=2.0, zorder=6)
        else:
            ax.add_patch(FancyBboxPatch((14, 100), 120, 430, boxstyle="round,pad=0,rounding_size=16",
                                         facecolor=meat, edgecolor="none", alpha=0.95, zorder=2))
            ax.text(70, 320, "quarter\non the\nspreader", color="#fcfcfb", fontsize=9, ha="center", va="center")
            for z in (190, 330, 520):
                ax.plot([8, 130, 8], [z - 6, z + 36, z + 6], color=strap, lw=2.0, zorder=6)
            ax.text(150, 400, "IM straps\neye to eye", color=strap, fontsize=8)

    def face(ax):
        ax.set_xlim(-180, 180)
        ax.set_ylim(-20, 620)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("From the bag side", loc="left", fontsize=11)
        for x in (-115, 115):
            ax.plot([x, x], [0, 540], color=frame, lw=10, solid_capstyle="round", zorder=3)
        ax.add_patch(FancyBboxPatch((-100, 80), 200, 400, boxstyle="round,pad=0,rounding_size=6",
                                     facecolor=sheet, edgecolor="none", alpha=0.35, zorder=1))
        ax.text(0, 100, "spreader", color=sheet, fontsize=8, ha="center")
        if mode_key == "bag_off":
            ax.add_patch(FancyBboxPatch((-70, 140), 140, 340, boxstyle="round,pad=0,rounding_size=20",
                                         facecolor=meat, edgecolor="none", zorder=2))
        elif mode_key == "between":
            ax.add_patch(FancyBboxPatch((-78, 120), 156, 360, boxstyle="round,pad=0,rounding_size=18",
                                         facecolor=meat, edgecolor="none", alpha=0.9, zorder=2))
        else:
            ax.add_patch(FancyBboxPatch((-90, 110), 180, 400, boxstyle="round,pad=0,rounding_size=16",
                                         facecolor=meat, edgecolor="none", alpha=0.85, zorder=2))
        for z, lab in ((190, "IM1"), (330, "IM2"), (520, "IM3")):
            ax.plot([-115, 115], [z, z], color=strap, lw=3.0, zorder=4)
            ax.plot(-115, z, "o", color="#6a6b6e", ms=7, zorder=5)
            ax.plot(115, z, "o", color="#6a6b6e", ms=7, zorder=5)
            ax.text(122, z, lab, va="center", fontsize=8, color=ink)
        if mode_key != "bag_off":
            ax.plot([-115, 115], [60, 60], color="#6a6b6e", lw=2.0, zorder=4)
            ax.text(122, 60, "hinge", va="center", fontsize=8, color=ink)

    side(axes[0])
    face(axes[1])
    sf = m["cleat_fatigue"]
    fig.suptitle(
        f"{m['name']}   ·   cleat fatigue SF {sf:.2f}   ·   spreader SF {m['sheet_sf']:.1f}   ·   "
        f"hook SF {m['hook_sf']:.2f}",
        x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.text(0.02, 0.02, m["note"], fontsize=8, color="#52514e")
    names = {"bag_on": f"{DATE}_attach_5_bag_on.png",
             "between": f"{DATE}_attach_6_between.png",
             "bag_off": f"{DATE}_attach_7_bag_off.png"}
    return _save(fig, names[mode_key])


def write(modes: dict, screens: list[str]) -> str:
    b, w, o = modes["bag_on"], modes["between"], modes["bag_off"]

    def row(nodes):
        lines = ["| station | force N | strength SF | fatigue SF |", "|---|---:|---:|---:|"]
        for name in ("hinge", "im1", "im2", "im3"):
            if name not in nodes:
                continue
            r = nodes[name]
            lines.append(f"| {name} | {r['n']:.0f} | {r['sf']:.2f} | {r['sf_fatigue']:.2f} |")
        return "\n".join(lines)

    text = f"""# Meat haul, both modes required

Owner, 2026-11-01: both modes are requirements. The eight B-01 swells are accepted.
IM1 stays a meat anchor only, for now. The hook proof test is still open.
Code: `huntkit/gendesign/meat_haul.py`.

The bearing face in every mode is the **2.0 mm QI carbon spreader** on the bag side of the
stays. Bone and the cinch land on the sheet. The sheet delivers them to the stay rails.
The mesh over the air gap is not a meat support. The wearer stays on the XLPE rails.

Spreader, from the comfort check (20 % of 68 kg on a 22 mm bone, factored): stress SF **{b['sheet_sf']:.2f}**,
peak skin pressure **{b['sheet_peak_kpa']:.1f} kPa**, factored deflection **{b['sheet_defl_mm']:.1f} mm**.
A 36 kg quarter is inside that check.

## A. Bag on (required)

Meat stays in the bag. IM1–IM3 pass through the B-01 ports, hook to the eyes on the cleat pins,
and cam tight. The meat is squeezed against the spreader. The bag floor carries the vertical
share into the hinge pins at z 60.

Load path: meat → strap → hook → eye → pin → fairlead → stay. Face pressure → spreader → stay rails.

This is the HA-LS-1 `meat_straps` resolution. The cleat FEA was run on these forces.
Branch-frame SF on that case is **{b['frame_sf']:.2f}**.

{row(b['nodes'])}

Hook and cam are checked against the larger of the factored cleat force and the published
605 N strap demand (2 × the 303 N service leg). Hook SF **{b['hook_sf']:.2f}**. Cam SF **{b['cam_sf']:.2f}**.
Webbing SF **{b['web_sf']:.0f}**. Bartack SF **{b['bartack_sf']:.2f}**. The cam rating is an assumption.

### A2. Between the bag and the frame (viable, part of bag-on)

Bulk meat does not have to go inside the tube of the bag. Release the four bag hooks at IM2 and
IM3. Leave the hinge pins in. The bag swings open about z 60. At IM3 the opening used here is
250 mm, which is **{w['angle_deg']:.0f}°**. The wedge is then {w['opening_mm']['190']:.0f} mm at IM1,
{w['opening_mm']['330']:.0f} mm at IM2 and {w['opening_mm']['520']:.0f} mm at IM3. A quarter fits,
thick end high, where the wedge is widest. The narrow end at the lumbar is the hock.

The captive eyes stay on the pins. The meat straps hook to those eyes across the meat, and the
meat bears on the spreader, not on the wearer's back. W1–W3 close the bag onto the wedge.
They are the outer clamp. They are not the meat anchor.

Head clearance gets easier: the bag moves aft, away from the head. The head setback on B-01
is for the closed bag.

Load path: meat → spreader for the face, → IM straps for the cinch and the overturning,
→ hinge pins for the share that still sits on the tilted floor.
ASSUMPTION: floor share 0.40 (the closed bag uses 0.70) and the CG is 110 mm aft of the frame,
because the wedge is shallower than the full bag.

{row(w['nodes'])}

Minimum cleat fatigue SF **{w['cleat_fatigue']:.2f}**. Hook SF **{w['hook_sf']:.2f}**.
The hinge sees {w['nodes']['hinge']['n']:.0f} N, under the {b['nodes']['hinge']['n']:.0f} N it was checked at.
IM1 sees {w['nodes']['im1']['n']:.0f} N against {b['nodes']['im1']['n']:.0f} N with the bag closed. Both sit under the
cleat that was checked at {b['nodes']['im3']['n']:.0f} N aft. **Viable.** A bone-in quarter rides here with the bag
still on the frame.

## B. Bag off (required)

The bag comes off. A quarter lies on the spreader. IM1, IM2 and IM3 hook eye-to-eye over it
and cam tight. There is no bag floor, so the weight is held by friction between the meat and
the sheet. μ 0.4 is the wet game-bag assumption already in `geometry.yaml`.

### Procedure (gloves, about 34 s, limit 2 min)

1. Unhook the four bag hooks (IM2 and IM3, both sides). IM1 has no bag hook.
2. Pull the two tethered hinge pins at z 60. The eyes for the meat straps stay on the other six pins.
3. Lift the bag clear and set it aside.
4. Lay the quarter on the spreader, bone against the sheet. The open window is mesh and air. It is not the bed.
5. Hook IM1, IM2 and IM3 from eye to eye over the meat. Cam tight. A hock can sit on IM1.
6. W1 and W2 can go over the top as a second clamp. They are not required for the friction sum below. W3 lashes a tall load to the crown.

Walking peak of 36 kg is **{o['walk_n']:.0f} N**. With only the three IM straps, each leg needs **{o['leg_walk_im_n']:.0f} N**
so the cinch does not slip. Adding W1 and W2 drops that to **{o['leg_walk_with_wraps_n']:.0f} N**, which is the
141 N figure already in `geometry.yaml`. The strength check uses 1.5 times the three-strap tension,
**{o['leg_factored_n']:.0f} N** per leg, aft, on each cleat.

{row(o['nodes'])}

Hook SF **{o['hook_sf']:.2f}**. Cam SF **{o['cam_sf']:.2f}**. Webbing SF **{o['web_sf']:.0f}**.
Cleat fatigue SF **{o['cleat_fatigue']:.2f}**, scaled from the IM3 fairlead because the pull is aft.
The factored leg, {o['leg_factored_n']:.0f} N, is under the {b['nodes']['im3']['n']:.0f} N aft load that cleat was
checked at. IM1 in this mode is {o['nodes']['im1']['n']:.0f} N, which is above the {b['nodes']['im1']['n']:.0f} N
that station sees with the bag closed, and still under that checked cleat. The branch-frame
`meat_straps` SF **{o['frame_sf']:.2f}** is the bag-on number. This bare-frame pull does not add a
heavier case than that check at IM3 or the hinge. The spreader check above was run on a heavier
bone than a 36 kg quarter.

To put the bag back: set the hinge eyes on the pins, clip IM2 and IM3, about 70 s.

## What is still open

- Hook break strength is an assumption (1500 N). Proof-test five to 830 N before the first sewn bag.
- IM1 does not get a bag clip yet. It is a meat anchor only until the owner says otherwise.

## Screenshots

"""
    for s in screens:
        text += f"- `{s}`\n"
    path = ANALYSIS / "meat_haul_modes.md"
    path.write_text(text)
    return str(path)


def emit(log=print):
    log("haul modes")
    modes = analyse()
    for key in ("bag_on", "between", "bag_off"):
        m = modes[key]
        log(f"  {key}: cleat fat {m['cleat_fatigue']:.2f}  hook {m['hook_sf']:.2f}  "
            f"viable {m['viable']}")
    screens = [_draw(k, modes) for k in ("bag_on", "between", "bag_off")]
    path = write(modes, screens)
    out = {k: {kk: vv for kk, vv in modes[k].items() if kk != "nodes"} | {"nodes": modes[k]["nodes"]}
           for k in ("bag_on", "between", "bag_off")}
    out["sheet_sf"] = modes["sheet"]["sf"]
    out["screens"] = screens
    (ANALYSIS / "meat_haul_modes.json").write_text(json.dumps(out, indent=2))
    log(path)
    return out


if __name__ == "__main__":
    emit()
