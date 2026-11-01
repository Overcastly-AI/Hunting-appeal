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
CAM_N = 1100.0                   # ASSUMPTION, DESIGN.md §4.5, 38 mm metal cam
WEB_N = 20016.0                  # poly_webbing_38mm record
# Under-straps. The belly is how far the cradle hangs below the straight line
# between the stays. A deeper belly keeps the cam tension down.
US1_Z = 95.0
US2_Z = 142.0
BELLY_MM = 70.0
HALF_SPAN_MM = 115.0
# Of the bag-floor vertical, this fraction moves onto the two under-straps.
# The rest stays on the hinge pins. ASSUMPTION.
CRADLE_SHARE = 0.55
US1_FRACTION = 0.60              # lower strap takes the greater share
DETACH_S = 40                    # was 34; two cam pops add about 6 s


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


def _theta() -> float:
    return float(np.arctan(BELLY_MM / HALF_SPAN_MM))


def cradle_tension(vertical_n: float) -> float:
    """Strap tension for a cradle whose two side legs rise at ``_theta``."""
    return float(vertical_n) / (2.0 * np.sin(_theta()))


def _pair(vertical_n: float, basis: dict) -> dict:
    """US1 and US2 anchor forces. ``vertical_n`` is the factored load in the cradle."""
    out = {}
    for name, frac in (("us1", US1_FRACTION), ("us2", 1.0 - US1_FRACTION)):
        t = cradle_tension(vertical_n * frac)
        th = _theta()
        n = t
        out[name] = {
            "n": n, "fy": float(t * np.cos(th)), "fz": float(-t * np.sin(th)),
            "vertical_n": float(vertical_n * frac), "tension_n": t,
            "sf": _scale(basis["sf"], basis["force_n"], n),
            "sf_fatigue": _scale(basis["sf_fatigue"], basis["force_n"], n),
            "from": basis.get("station", "cradle"),
        }
    return out


def _shift_hinge(row: dict, keep: float, basis: dict) -> dict:
    """Leave ``keep`` of the hinge's vertical force on the pin. Rescale from the hinge FEA."""
    fy, fz = float(row["fy"]), float(row["fz"]) * keep
    n = float(np.hypot(fy, fz))
    out = dict(row)
    out.update({"n": n, "fy": fy, "fz": fz,
                "sf": _scale(basis["sf"], basis["force_n"], n),
                "sf_fatigue": _scale(basis["sf_fatigue"], basis["force_n"], n)})
    return out


def _friction_leg(weight_n: float, n_straps: int) -> float:
    """Tension in one strap leg so μ times the strap's normal force holds ``weight_n``.

    A strap hooked eye-to-eye has two legs and squeezes with about 2 T. Geometry.yaml
    uses this for the 141 N figure (5 straps).
    """
    return weight_n / (MU * n_straps * 2.0)


def analyse(cradle_fea: dict | None = None) -> dict:
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

    # Under-straps take part of the floor vertical off the hinge pins.
    # Bag-off has no floor: the cradle carries the quarter and the IM straps only cinch.
    us_basis = cradle_fea if cradle_fea else hinge
    if "force_n" not in us_basis:
        us_basis = {**us_basis, "force_n": us_basis.get("requested_n", us_basis["n"]),
                    "station": "us1"}

    def with_cradle(nodes, cradle_vertical, keep_hinge):
        out = {k: dict(v) for k, v in nodes.items() if k != "hinge"}
        if "hinge" in nodes and keep_hinge > 0:
            out["hinge"] = _shift_hinge(nodes["hinge"], keep_hinge, hinge)
        out.update(_pair(cradle_vertical, us_basis))
        return out

    floor_on = 2.0 * abs(bag_on["hinge"]["fz"])
    bag_on = with_cradle(bag_on, CRADLE_SHARE * floor_on, 1.0 - CRADLE_SHARE)
    floor_bay = 2.0 * abs(bay_c["hinge"]["fz"])
    bay_c = with_cradle(bay_c, CRADLE_SHARE * floor_bay, 1.0 - CRADLE_SHARE)

    walk = QUARTER_KG * G * 1.6
    leg3 = _friction_leg(walk, 3)
    leg5 = _friction_leg(walk, 5)
    # Strength case for the bare frame: 1.5 on the 1.6 g walking peak.
    w_off = walk * 1.5
    cinch = 150.0 * 1.5
    off_c = mixed({
        "im1": {"n": cinch, "fy": cinch, "fz": 0.0},
        "im2": {"n": cinch, "fy": cinch, "fz": 0.0},
        "im3": {"n": cinch, "fy": cinch, "fz": 0.0},
    })
    off_c.update(_pair(w_off, us_basis))

    web = float(load("poly_webbing_38mm").require("breaking_strength_n"))
    assert abs(web - WEB_N) < 1.0

    # Opening geometry for the wedge. Hinge z 60, IM3 z 520, 250 mm at IM3.
    rise = 520.0 - 60.0
    opening = {z: 250.0 * (z - 60.0) / rise for z in (190.0, 330.0, 520.0)}
    angle = float(np.degrees(np.arctan(250.0 / rise)))

    def pack(name, required, nodes, note, strap_n):
        cleat_fat = min(float(r["sf_fatigue"]) for r in nodes.values())
        cleat_sf = min(float(r["sf"]) for r in nodes.values())
        hinge_n = nodes.get("hinge", {}).get("n", strap_n)
        return {
            "name": name, "required": required, "viable": bool(cleat_sf >= 1.0 and cleat_fat >= 1.0),
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
            "Quarter in the under-strap cradle, cinched to the spreader by IM1–IM3.",
            cinch,
        ),
    }
    for key, vertical in (
        ("bag_on", CRADLE_SHARE * floor_on),
        ("between", CRADLE_SHARE * floor_bay),
        ("bag_off", w_off),
    ):
        t = max(modes[key]["nodes"]["us1"]["tension_n"], modes[key]["nodes"]["us2"]["tension_n"])
        modes[key]["cradle_tension_n"] = t
        modes[key]["cradle_cam_sf"] = CAM_N / t
        modes[key]["cradle_web_sf"] = web / t
        modes[key]["cradle_vertical_n"] = vertical
        modes[key]["viable"] = bool(modes[key]["viable"] and modes[key]["cradle_cam_sf"] >= 1.0)
    modes["cradle"] = {
        "us1_z": US1_Z, "us2_z": US2_Z, "belly_mm": BELLY_MM,
        "theta_deg": float(np.degrees(_theta())),
        "share": CRADLE_SHARE, "us1_fraction": US1_FRACTION,
        "detach_s": DETACH_S,
        "basis": "cradle_fea" if cradle_fea else "hinge_scaled",
    }
    modes["between"]["opening_mm"] = {str(int(k)): v for k, v in opening.items()}
    modes["between"]["angle_deg"] = angle
    modes["between"]["viable"] = modes["between"]["viable"] and opening[330.0] >= 120.0
    modes["bag_off"]["leg_walk_im_n"] = leg3
    modes["bag_off"]["leg_walk_with_wraps_n"] = leg5
    modes["bag_off"]["leg_factored_n"] = leg3 * 1.5
    modes["bag_off"]["walk_n"] = walk
    modes["bag_on"]["frame_sf"] = branch["cases"]["meat_straps"]
    # Bag-off cleat forces are inside the meat_straps envelope, so the frame SF stands.
    modes["bag_off"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["between"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["sheet"] = {"sf": sheet["sf"], "peak_kpa": sheet["peak_kpa"], "defl_mm": sheet["defl_mm"],
                      "name": sheet["name"]}
    web_m = load("poly_webbing_38mm")
    pa = load("pa12_cf_fdm_paht")
    anchor_g = float((cradle_fea or {}).get("added_g", 6.2))
    parts = {
        "printed anchors (4)": 4 * anchor_g,
        "7075 pins (4)": 4 * 2.41,
        "UHMWPE sleeves (4)": 4 * 0.29,
        "38 mm cams (2)": 2 * 22.0,
        "tri-glide keepers (2)": 2 * 3.0,
        "38 mm webbing, 1.10 m": 1.10 * float(web_m.require("mass_g_m")),
        "bag-floor channels": 8.0,
    }
    plastic = parts["printed anchors (4)"]
    filament = plastic * 1.08 * float(pa.require("print_cost_usd_per_g"))
    modes["cradle"]["mass_g"] = float(sum(parts.values()))
    modes["cradle"]["parts_g"] = parts
    modes["cradle"]["cost_usd"] = filament * 1.15 + 4 * 2.50 + 2 * 4.00 + 1.10 * float(web_m.cost_usd["value"]) + 2 * 0.40
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
        for z, lab in ((60, "hinge"), (95, "US1"), (142, "US2"), (190, "IM1"), (330, "IM2"), (520, "IM3")):
            ax.add_patch(Circle((0, z), 6, facecolor="#6a6b6e", edgecolor=ink, lw=0.4, zorder=5))
            ax.text(-8, z, lab, ha="right", va="center", fontsize=7.5, color=ink)
        # cradle: aft and down from US1 and US2, under the floor
        ax.plot([0, 55, 120], [95, 25, 25], color="#1baf7a", lw=2.4, zorder=6)
        ax.plot([0, 70, 140], [142, 55, 55], color="#1baf7a", lw=2.4, zorder=6)
        ax.text(125, 18, "under-straps", color="#1baf7a", fontsize=8)
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
        for z, lab, col in ((95, "US1", "#1baf7a"), (142, "US2", "#1baf7a"),
                            (190, "IM1", strap), (330, "IM2", strap), (520, "IM3", strap)):
            ax.plot([-115, 115], [z, z], color=col, lw=3.0, zorder=4)
            ax.plot(-115, z, "o", color="#6a6b6e", ms=6, zorder=5)
            ax.plot(115, z, "o", color="#6a6b6e", ms=6, zorder=5)
            ax.text(122, z, lab, va="center", fontsize=8, color=ink)
        if mode_key != "bag_off":
            ax.plot([-115, 115], [60, 60], color="#6a6b6e", lw=2.0, zorder=4)
            ax.text(122, 60, "hinge", va="center", fontsize=8, color=ink)

    side(axes[0])
    face(axes[1])
    sf = m["cleat_fatigue"]
    fig.suptitle(
        f"{m['name']}   ·   anchor fatigue SF {sf:.2f}   ·   cradle cam SF {m['cradle_cam_sf']:.2f}",
        x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.text(0.02, 0.02, m["note"], fontsize=8, color="#52514e")
    names = {"bag_on": f"{DATE}_attach_9_cradle_bag_on.png",
             "between": f"{DATE}_attach_6_between.png",
             "bag_off": f"{DATE}_attach_10_cradle_bag_off.png"}
    return _save(fig, names[mode_key])


def write(modes: dict, screens: list[str]) -> str:
    b, w, o = modes["bag_on"], modes["between"], modes["bag_off"]

    def row(nodes):
        lines = ["| station | force N | strength SF | fatigue SF |", "|---|---:|---:|---:|"]
        for name in ("hinge", "us1", "us2", "im1", "im2", "im3"):
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
stays. Two **38 mm under-straps** also run under the bag, from fairleads at z {US1_Z:.0f} and
z {US2_Z:.0f}. With the bag on they cinch the floor up to the frame, and the bag shell shares
the vertical load with the hinge pins. With the bag off they are the cradle, so the quarter
does not hang on friction alone. IM1–IM3 still cinch the meat against the spreader.

Each strap is a sewn eye on the left pin, under the floor, and a 38 mm cam on the right pin.
A tri-glide sits behind the cam so a slip cannot lengthen the cradle. The belly under the
anchor line is specified at **{BELLY_MM:.0f} mm**, which keeps the side legs at
**{modes['cradle']['theta_deg']:.0f}°** and the cam inside its assumed slip rating.
25 mm webbing was set aside: its ladder lock slips at 300 N and its side-release breaks at
450 N, both under the factored cradle tension.

Spreader, from the comfort check (20 % of 68 kg on a 22 mm bone, factored): stress SF **{b['sheet_sf']:.2f}**,
peak skin pressure **{b['sheet_peak_kpa']:.1f} kPa**, factored deflection **{b['sheet_defl_mm']:.1f} mm**.
A 36 kg quarter is inside that check.

Of the bag-floor vertical, **{CRADLE_SHARE:.0%}** moves onto the under-straps and the rest stays
on the hinge pins (ASSUMPTION). The lower strap takes {US1_FRACTION:.0%} of that cradle load.

## A. Bag on (required)

Meat stays in the bag. IM1–IM3 hook to the cleat eyes and cam the meat against the spreader.
The two under-straps run through open channels in the bag floor and are cammed tight, so the
floor is a sling between the hinge pins and the cradle anchors.

Load path: meat → bag floor → under-straps and hinge pins for the vertical share. IM straps →
cleats for the cinch and the overturning. Face pressure → spreader → stay rails.

Branch-frame SF on `meat_straps` is **{b['frame_sf']:.2f}**. Under-strap tension **{b['cradle_tension_n']:.0f} N**,
cam SF **{b['cradle_cam_sf']:.2f}**, webbing SF **{b['cradle_web_sf']:.0f}**.

{row(b['nodes'])}

Hook and cam on the IM straps are checked against the larger of the factored IM force and the
published 605 N strap demand. Hook SF **{b['hook_sf']:.2f}**. IM-cam SF **{b['cam_sf']:.2f}**.
The under-strap cam is the line above, not this one. Bartack SF **{b['bartack_sf']:.2f}**.

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

Minimum cleat fatigue SF **{w['cleat_fatigue']:.2f}**. IM hook SF **{w['hook_sf']:.2f}**.
Under-strap tension **{w['cradle_tension_n']:.0f} N**, cam SF **{w['cradle_cam_sf']:.2f}**.
The hinge, after the cradle takes its share, sees {w['nodes']['hinge']['n']:.0f} N.
**Viable.** The under-straps stay cammed, so the open bag floor does not dump the low end of the quarter.

## B. Bag off (required)

The bag comes off. The two under-straps stay on the frame and become the cradle. The quarter
sits in them. IM1–IM3 still hook eye-to-eye and cam the meat against the spreader so it cannot
tip off the cradle. Friction is only a reserve. μ 0.4 and the old 141 N leg (five straps) are
the reserve numbers, not the design path.

### Procedure (gloves, about {DETACH_S} s, limit 2 min)

1. Pop the two under-strap cams and lift the bag floor out of the open channels. The straps stay on their pins. About 6 s.
2. Unhook the four bag hooks (IM2 and IM3, both sides). IM1 has no bag hook.
3. Pull the two tethered hinge pins at z 60.
4. Lift the bag clear.
5. Set the quarter in the cradle, bone toward the spreader. Cam the two under-straps until the belly is about {BELLY_MM:.0f} mm.
6. Hook IM1–IM3 eye-to-eye over the meat and cam them. A hock can sit on IM1.

Walking peak of 36 kg is **{o['walk_n']:.0f} N**. The strength check is 1.5 times that,
**{o['cradle_vertical_n']:.0f} N**, all of it in the cradle. Lower strap tension
**{o['nodes']['us1']['tension_n']:.0f} N**. Cam SF **{o['cradle_cam_sf']:.2f}**.
The IM cinch used here is the 150 N hand tension times 1.5, **{o['hook_n']:.0f} N** per leg.
Hook SF on that cinch **{o['hook_sf']:.2f}**.

{row(o['nodes'])}

The cradle anchors are the same fairlead as the hinge, on the solid lower stay. Their fatigue
SF is scaled from the fine-mesh solve of the governing cradle vector when that solve is on file,
and from the hinge solve otherwise (`{modes['cradle']['basis']}`).

To put the bag back: pins in, bag hooks on, floor channels over the cradle straps, cams tight.
About 80 s.

## What is still open

- Hook and cam ratings are assumptions (hook 1500 N, cam slip 1100 N). Proof-test five of each to 830 N before the first sewn bag. The under-strap cam is in this test.
- IM1 does not get a bag clip yet. It is a meat anchor only until the owner says otherwise.

## Mass and cost of the under-straps

| part | g |
|---|---:|
"""
    for name, grams in modes["cradle"]["parts_g"].items():
        text += f"| {name} | {grams:.1f} |\n"
    text += f"| **added** | **{modes['cradle']['mass_g']:.0f}** |\n\n"
    text += (f"About **${modes['cradle']['cost_usd']:.0f}** on top of the fairlead set. "
             f"Detach time **{DETACH_S} s** (the two cam pops are about 6 s of that). "
             f"Pack with the cradle is the previous 2979 g plus this added mass.\n\n")
    text += "## Screenshots\n\n"
    for s in screens:
        text += f"- `{s}`\n"
    path = ANALYSIS / "meat_haul_modes.md"
    path.write_text(text)
    return str(path)


def plot_anchor_closeup() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.bag_attach import SCALE, _march
    from huntkit.gendesign.frame_branch import frame_sdf
    from huntkit.gendesign.frame_render import autocrop, raster
    from huntkit.gendesign.render import _style
    _style()
    lo = np.array([70.0, -28.0, 40.0])
    hi = np.array([160.0, 48.0, 175.0])
    mesh = _march(lambda p: frame_sdf(p, SCALE), lo, hi, 0.85)
    fig = plt.figure(figsize=(10.4, 4.6))
    views = (("bag side", 14, -70), ("side", 8, 8), ("above the two anchors", 64, -36))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster([(mesh, (0.32, 0.33, 0.36))], el, az, size=420, spec=0.18)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Under-strap anchors at z 95 and z 142, above the hinge pin",
                 x=0.02, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return _save(fig, f"{DATE}_attach_8_cradle_anchors.png")


def plot_cradle_fea(row: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.render import _style
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    ax = axes[0]
    names = ["strength", "fatigue"]
    vals = [row["sf"], row["sf_fatigue"]]
    ax.barh(names, vals, color=["#1baf7a" if v >= 1 else "#d6342a" for v in vals])
    ax.axvline(1.0, color="#0b0b0b", ls="--", lw=1)
    ax.set_xlabel("safety factor")
    ax.set_title(f"Cradle anchor  ·  {row['requested_n']:.0f} N  ·  {row['h_mm']:.0f} mm mesh",
                 loc="left", fontweight="bold")
    slab = row["slab"]
    finite = np.isfinite(slab)
    show = np.where(finite, slab, np.nan)
    vals_fi = show[finite]
    vmax = float(np.percentile(vals_fi, 99)) if vals_fi.size else 1.0
    im = axes[1].imshow(show.T, origin="lower", cmap="magma", vmin=0, vmax=max(0.25, vmax))
    axes[1].set_title("Failure index through one cheek", loc="left", fontsize=11)
    axes[1].set_xlabel("y, toward the bag")
    axes[1].set_ylabel("z, up the stay")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04).set_label("failure index")
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_11_cradle_fea.png")


def emit(log=print):
    from huntkit.gendesign.bag_attach import _fatigue_sf, _creep_sf, _paht, solve_fairlead
    from huntkit.gendesign.frame_branch import stay_radius
    walk = QUARTER_KG * G * 1.6
    us1_v = US1_FRACTION * walk * 1.5
    tension = cradle_tension(us1_v)
    th = _theta()
    force = np.array([tension * np.cos(th), -tension * np.sin(th)])
    radius = float(stay_radius(US1_Z, 1.05))
    log(f"FEA cradle anchor, stay r {radius:.1f} mm, tension {tension:.0f} N")
    row = solve_fairlead(radius, force, h=1.0, label="us1 1.00 mm")
    pa = _paht()
    row["sf_fatigue"] = _fatigue_sf(row["fi99"], 1.6 * 1.5, pa["fat"])
    row["sf_creep"] = _creep_sf(row["fi99"], 1.6 * 1.5, pa["rupture"])
    row["station"] = "us1"
    row["force_n"] = row["requested_n"]
    log(f"  FI99 {row['fi99']:.3f}  SF {row['sf']:.2f}  fat {row['sf_fatigue']:.2f}  "
        f"applied {row['applied_n']:.0f}/{row['requested_n']:.0f}")
    basis = {k: row[k] for k in ("sf", "sf_fatigue", "force_n", "station", "added_g", "fi99", "h_mm")}
    (ANALYSIS / "cradle_fea.json").write_text(json.dumps(basis, indent=2))
    modes = analyse(basis)
    for key in ("bag_on", "between", "bag_off"):
        m = modes[key]
        log(f"  {key}: cleat fat {m['cleat_fatigue']:.2f}  hook {m['hook_sf']:.2f}  "
            f"cam {m['cradle_cam_sf']:.2f}  viable {m['viable']}")
    screens = [
        plot_anchor_closeup(),
        _draw("bag_on", modes),
        _draw("bag_off", modes),
        plot_cradle_fea(row),
    ]
    # keep the between drawing current as well
    screens.insert(2, _draw("between", modes))
    path = write(modes, screens)
    out = {k: {kk: vv for kk, vv in modes[k].items() if kk != "nodes"} | {"nodes": modes[k]["nodes"]}
           for k in ("bag_on", "between", "bag_off")}
    out["sheet_sf"] = modes["sheet"]["sf"]
    out["screens"] = screens
    (ANALYSIS / "meat_haul_modes.json").write_text(json.dumps(out, indent=2, default=float))
    log(path)
    return out


if __name__ == "__main__":
    emit()
