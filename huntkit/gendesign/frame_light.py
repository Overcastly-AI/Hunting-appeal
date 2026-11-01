"""Cut the pack back toward 5.0 lb without giving up the back system or a smooth ladder.

The solid smooth ladder is 1291 g of PAHT because an 8 mm wall around a long sleeve bore,
plus a solid lumbar pan, is a lot of nylon. This module compares four frames that all keep
the 2.0 mm QI carbon spreader and the 10 mm stay rails:

  (a) hollow PAHT-CF stays (bead along the stay, wall thick enough to pass fatigue)
  (b) the v2 carbon tubes inside a 1.2 mm printed fairing (the fairing is the look, not the structure)
  (c) the v2 carbon-tube ladder itself, with the wrapped nodes it already has
  (d) nothing lighter passed. A thinner PAHT stay (OD 26, wall 3.5) misses fatigue.

Strength is the beam / first-ply model in huntkit.fea (the right check for a 0.8 mm carbon
wall; a 4 mm voxel would invent a wall five times too thick). Reported SF is min member SF
divided by the HA-LS-1 required factor, worst of 15 / 19 / 23 in. Fatigue is the HA-LS-1
screen: 1e5 cycles at 1.6 g, CFRP at half the knocked-down first-ply strength, PAHT at
0.3 of the knocked-down tensile strength.

Run: python -m huntkit.gendesign.frame_light
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.materials import load

from . import frame_production as prod
from .frame_smooth import choose_back, options

DATE = "20261101"
SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"

# frame.yaml mass_g, the two stay lines. The printed stay replaces these and nothing else.
CARBON_STAY_G = 19.6 + 60.4
TUBE_FRAME_G = 569.2          # geometry.yaml: frame.yaml 577 - Ti insert 28 + SLM mount 20.2
# Crown rack, pawl housing and pulley guides are already inside the 569.2 g. They are the only
# PAHT on the production frame. Volume from mass / density.
RACK_G = 44.0


def _save(fig, name: str) -> str:
    from .render import save
    path = SCREENS / name
    save(fig, path)
    art = Path("/opt/cursor/artifacts/prodframe")
    art.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(path, art / name)
    out = REPO_ROOT / "outputs" / "screens"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, out / name)
    return str(path)


def comfort() -> dict:
    """The back system the owner kept. Same stack on every frame option."""
    row = choose_back(options())
    return {"name": row["name"], "peak_kpa": row["peak_kpa"], "avg_kpa": row["avg_kpa"],
            "spread_mm": row["spread_mm"], "defl_mm": row["defl_mm"], "sheet_g": row["sheet_g"],
            "foam_g": row["foam_g"], "foam_delta_g": max(row["foam_g"] - 11.5, 0.0),
            "passes": bool(row["passes"])}


def paht_material() -> dict:
    pa = load("pa12_cf_fdm_paht")
    knock = float(pa.get("env_knockdown_ratio", 0.8))
    return {
        "id": "pa12_cf_fdm_paht",
        "name": "PAHT-CF stay tube",
        "category": "polymers",
        "properties": {
            "density_kg_m3": float(pa.require("density_kg_m3")),
            "youngs_modulus_mpa": float(pa.require("youngs_modulus_xy_mpa")),
            "shear_modulus_mpa": float(pa.require("youngs_modulus_xy_mpa")) / 2.7,
            "poisson": 0.35,
            # Flat print, layer normal = frame y, bead along the stay. Bending stress is in-plane.
            "yield_strength_mpa": knock * float(pa.require("tensile_strength_xy_mpa")),
        },
        "fatigue_ratio": float(pa.get("fatigue_1e5_ratio", 0.3)),
        "rho": float(pa.require("density_kg_m3")),
    }


STAY_GROUPS = {"stay_lower_L", "stay_lower_R", "stay_upper_L", "stay_upper_R"}


def _length_mm(fm, groups) -> float:
    total = 0.0
    for m in fm["members"]:
        if m["group"] not in groups:
            continue
        a, b = m["nodes"]
        total += float(np.linalg.norm(np.array(fm["nodes"][b]) - np.array(fm["nodes"][a])))
    return total


def _study(fm):
    from huntkit.fea.analysis import run_study
    from huntkit.fea.load_standard import ls1_cases
    return run_study(fm, cases=ls1_cases(), label="light")


def _envelope(build):
    """Worst torso of SF/required, and the fatigue SF of the static-carry members."""
    cases = {}
    where = {}
    fat = 1e9
    fat_where = ""
    for torso in (15.0, 19.0, 23.0):
        study = _study(build(torso))
        for name, r in study["results"].items():
            ratio = float(r.min_sf / r.meta["required_sf"])
            if name not in cases or ratio < cases[name]:
                cases[name] = ratio
                where[name] = f"{r.critical_member['group']} ({torso:.0f} in)"
        static = study["results"]["static_carry"]
        for m in static.members:
            if m["group"] == "lumbar_plate_shear":
                continue
            ratio = 0.3 if m["group"] in STAY_GROUPS and "von_mises" in m else 0.5
            # PAHT stays are the only isotropic members we introduce. Carbon, including the
            # lumbar plate, stays on the composite fatigue screen (half of first-ply).
            if "von_mises" in m and m["group"] in STAY_GROUPS:
                ratio = 0.3
            else:
                ratio = 0.5
            sf = ratio * float(m["sf"]) / 1.6
            if sf < fat:
                fat = sf
                fat_where = f"{m['group']} ({torso:.0f} in)"
    return {"cases": cases, "where": where, "sf_min": min(cases.values()),
            "governing": min(cases, key=cases.get), "sf_fatigue": fat, "fatigue_where": fat_where}


def carbon_frame():
    from huntkit.fea.frames import build_frame_from_yaml

    def build(torso):
        return build_frame_from_yaml("designs/pack_5200/frame.yaml", torso_in=torso, extension_posts=True)

    env = _envelope(build)
    fm = build(19.0)
    env["stay_length_mm"] = _length_mm(fm, STAY_GROUPS)
    return env


def paht_stays(od: float, wall: float, stay_length_mm: float):
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.sections import tube_round
    mat = paht_material()
    sec = tube_round(od, wall)

    def build(torso):
        fm = build_frame_from_yaml("designs/pack_5200/frame.yaml", torso_in=torso, extension_posts=True)
        for m in fm["members"]:
            if m["group"] in STAY_GROUPS:
                m["section"] = sec
                m["material"] = mat
        return fm

    env = _envelope(build)
    area = float(sec.A)
    env["stay_g"] = stay_length_mm * area * mat["rho"] / 1e6
    env["od_mm"] = od
    env["wall_mm"] = wall
    return env


def fairing_g(stay_length_mm: float, skin_mm: float = 1.2, od_stay: float = 24.0,
              bar_length_mm: float = 460.0, od_bar: float = 22.0) -> float:
    """Non-structural PAHT skin. Mass only. It does not enter the strength check."""
    rho = float(load("pa12_cf_fdm_paht").require("density_kg_m3"))
    stay = stay_length_mm * np.pi * od_stay * skin_mm * rho / 1e6
    bars = bar_length_mm * np.pi * od_bar * skin_mm * rho / 1e6
    return float(stay + bars)


def print_hours(grams: float, rho: float = 1060.0) -> float:
    """Same flow assumption as the shop sheet: 8 mm³/s, 8 % waste. ``rho`` is kg/m³."""
    volume_mm3 = grams / rho * 1e6
    return volume_mm3 * 1.08 / 8.0 / 3600.0


def tube_cost_usd() -> dict:
    """Material dollars. Tube price is the roll-wrapped record ($30/m at ~16 mm), scaled by
    diameter. ASSUMPTION on everything that is not that record or the carbon-plate record."""
    # cut lengths from frame.yaml stock, metres
    tubes = [
        ("stays OD 20, 2 x 525 mm", 1.050, 20.0),
        ("crown legs OD 16, 2 x 430 mm", 0.860, 16.0),
        ("mid bar OD 18", 0.210, 18.0),
        ("upper bar OD 22", 0.210, 22.0),
        ("crown top bar OD 18", 0.214, 18.0),
        ("spine OD 20", 0.300, 20.0),
    ]
    rate = 30.0  # usd per m at 16 mm, cfrp_rollwrapped_tube
    rows = []
    stay_usd = 0.0
    for name, length_m, od in tubes:
        usd = rate * (od / 16.0) * length_m
        rows.append({"item": name, "usd": usd})
        if name.startswith("stays"):
            stay_usd = usd
    # lumbar pan 110.4 g at 1.5 mm, rho 1550 → area, plate record is $350/m² at 3 mm
    # 110.4 g, 1.5 mm, 1550 kg/m³. Mass is grams, so divide by 1000 before the kg formula.
    lumbar_area_m2 = (110.4 / 1000.0) / (1550.0 * 1.5e-3)
    lumbar = 350.0 * (1.5 / 3.0) * lumbar_area_m2
    rows.append({"item": "lumbar plate material (record, scaled by thickness)", "usd": lumbar})
    rows.append({"item": "wrap fabric, epoxy, shrink tape (ASSUMPTION)", "usd": 25.0})
    rows.append({"item": "MMA", "usd": 2.0})
    rows.append({"item": "7075 foot boots (ASSUMPTION)", "usd": 8.0})
    rows.append({"item": "UHMWPE bushings (ASSUMPTION)", "usd": 5.0})
    rows.append({"item": "SLM Ti hip mount, 20 g (ASSUMPTION $35)", "usd": 35.0})
    rack_usd = RACK_G * 1.08 * 0.08
    rows.append({"item": "PAHT rack, pawl, guides", "usd": rack_usd})
    rows.append({"item": "machine, rack only", "usd": print_hours(RACK_G)})
    return {"rows": rows, "tubes_and_frame": sum(r["usd"] for r in rows), "stay_tubes": stay_usd}


def pack_g(frame_g: float, foam_delta: float) -> float:
    return prod.SOFT_GOODS_G + foam_delta + frame_g


def _row(name, kind, frame_g, foam_delta, env, peak, spread, smooth, cost, hours, note):
    return {
        "name": name, "kind": kind, "frame_g": frame_g,
        "pack_g": pack_g(frame_g, foam_delta), "pack_lb": pack_g(frame_g, foam_delta) / 453.59237,
        "sf_min": env["sf_min"], "governing": env["governing"], "sf_fatigue": env["sf_fatigue"],
        "cases": env["cases"], "where": env["where"],
        "peak_kpa": peak, "spread_mm": spread, "smooth": smooth,
        "cost_usd": cost, "print_h": hours, "note": note,
        "passes": env["sf_min"] >= 1.0 and env["sf_fatigue"] >= 1.0 and peak <= 14.0 and spread >= 40.0,
    }


def choose(rows: list[dict]) -> dict:
    passing = [r for r in rows if r["passes"]]
    return min(passing or rows, key=lambda r: (r["pack_g"], -r["sf_min"]))


def plot_options(rows, winner) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S2, S3
    _style()
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    offsets = {
        "Carbon-tube ladder": (-8, 12),
        "Carbon tubes + 1.2 mm fairing": (8, -14),
        "PAHT stays OD 26 × 3.5 mm": (8, 10),
        "PAHT stays OD 28 × 4 mm": (8, -16),
        "Solid PAHT ladder (retired)": (-8, 10),
    }
    short = {
        "Carbon-tube ladder": "carbon ladder",
        "Carbon tubes + 1.2 mm fairing": "tubes + fairing",
        "PAHT stays OD 26 × 3.5 mm": "PAHT OD 26, fails fatigue",
        "PAHT stays OD 28 × 4 mm": "PAHT OD 28",
        "Solid PAHT ladder (retired)": "solid ladder",
    }
    for r in rows:
        color = S3 if r["passes"] else "#b0aea8"
        ax.scatter(r["pack_lb"], r["sf_min"], s=90, c=color, zorder=3)
        dx, dy = offsets.get(r["name"], (6, 6))
        ax.annotate(short.get(r["name"], r["name"]), (r["pack_lb"], r["sf_min"]),
                    textcoords="offset points", xytext=(dx, dy), fontsize=8,
                    ha="right" if dx < 0 else "left")
    ax.scatter([winner["pack_lb"]], [winner["sf_min"]], s=220, facecolors="none", edgecolors="black", lw=1.4)
    ax.axhline(1.0, color=S2, ls="--", lw=1.0)
    ax.axvline(5.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("pack mass (lb)")
    ax.set_ylabel("minimum SF / required, worst torso")
    ax.set_title("Frame options, same back system", loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_light_1_options.png")


def plot_mass(parts: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1
    _style()
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    names = list(parts)
    vals = [parts[n] for n in names]
    ax.barh(names, vals, color=S1)
    for i, v in enumerate(vals):
        ax.text(v + 8, i, f"{v:.0f} g", va="center", fontsize=8)
    ax.set_xlabel("grams")
    ax.set_title("Where the grams are", loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_light_3_mass.png")


def plot_fea(cases: dict, fatigue: float) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1
    _style()
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    names = list(cases)
    vals = [cases[n] for n in names]
    colors = ["#1baf7a" if v >= 1.3 else "#eda100" if v >= 1.0 else "#d6342a" for v in vals]
    ax.barh(names, vals, color=colors)
    ax.axvline(1.0, color=S1, ls="--", lw=1.0)
    ax.set_xlabel("SF / required factor, worst torso")
    ax.set_title(f"Carbon-tube ladder  ·  min {min(vals):.2f}  ·  fatigue {fatigue:.2f}",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_light_4_fea.png")


def plot_views() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from huntkit.viz3d.model import build_pack
    from huntkit.viz3d.params import load_params
    from .frame_render import autocrop, raster, simplify
    from .render import _style, SURF
    _style()
    pack = build_pack(load_params(overrides={"fea": {"enabled": False}, "frame_type": "tube",
                                             "mannequin": {"enabled": False}}))
    meshes = []
    for part in pack.parts:
        # crown_wrap is the bag collar. Only the frame group: stays, bars, plate, crown, spreader.
        if part.group != "frame" or part.torso not in (None, 19.0):
            continue
        meshes.append(part.mesh)
    mesh = simplify(trimesh.util.concatenate(meshes), target=24000)
    fig = plt.figure(figsize=(11.2, 4.8))
    views = (("bag side", 16, 28), ("wearer side", 12, 200), ("side", 4, 90), ("top", 78, 20))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 4, i + 1)
        img, info = raster([(mesh, (0.22, 0.24, 0.26))], el, az, size=360, spec=0.25)
        ax.imshow(autocrop(img, info["mask"], pad=6))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Production frame: carbon-tube ladder and the spreader", x=0.02, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.patch.set_facecolor(SURF)
    return _save(fig, f"{DATE}_light_2_frame_views.png")


def write_doc(rows, winner, cost, screens, sheet) -> str:
    lines = [
        "# Mass cut: keep the back, drop the solid nylon stays",
        "",
        "The back system does not change: 2.0 mm QI carbon spreader, two 100 × 420 × 10 mm XLPE rails, "
        "mesh over the air gap. Peak skin pressure "
        f"**{sheet['peak_kpa']:.1f} kPa**, spread **{sheet['spread_mm']:.0f} mm**. "
        "Code: `huntkit/gendesign/frame_light.py`.",
        "",
        "The solid smooth ladder (1291 g of PAHT, pack 7.51 lb, about 46 h to print) is retired as the "
        "structure. Hollowing that same outer shape saves almost nothing: the section is already about "
        "as thick as an 8 mm wall. A real hollow stay is a smaller tube, checked here as a beam.",
        "",
        "## Recommendation",
        "",
        f"**{winner['name']}.** {winner['note']}",
        "",
        f"- Frame **{winner['frame_g']:.0f} g**. Pack **{winner['pack_g']:.0f} g ({winner['pack_lb']:.2f} lb)**.",
        f"- Minimum SF/required **{winner['sf_min']:.2f}** ({winner['governing']}). "
        f"Fatigue SF **{winner['sf_fatigue']:.2f}**.",
        f"- Comfort peak **{winner['peak_kpa']:.1f} kPa**, spread **{winner['spread_mm']:.0f} mm**.",
        f"- Print time about **{winner['print_h']:.1f} h** (the rack, pawl and guides, not the stays).",
        f"- Material cost about **${winner['cost_usd']:.0f}**. Most of that is tubes, the lumbar plate, "
        "the Ti mount and the spreader, not filament.",
        "",
        "5.0 lb (2268 g) is still missed, by about "
        f"**{winner['pack_g'] - 2268:.0f} g**. The tube frame was already 569 g before the spreader. "
        "The spreader is 193 g and the comfort check does not let it get thinner. Soft goods are 1655 g. "
        "Those three lines are the pack. A lighter frame than the carbon tubes did not pass.",
        "",
        "## Options",
        "",
        "| option | frame g | pack lb | min SF/req | fatigue | peak kPa | spread mm | print h | cost USD | pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['frame_g']:.0f} | {r['pack_lb']:.2f} | {r['sf_min']:.2f} | "
            f"{r['sf_fatigue']:.2f} | {r['peak_kpa']:.1f} | {r['spread_mm']:.0f} | {r['print_h']:.1f} | "
            f"{r['cost_usd']:.0f} | {'yes' if r['passes'] else 'no'} |"
        )
    lines += [
        "",
        "SF/req is the beam-model member safety factor divided by the HA-LS-1 factor, worst of 15, 19 and "
        "23 in. The retired solid ladder's 1.39 was a 4 mm voxel layer-index on factored loads, a different "
        "model of a different frame. Both numbers mean the same thing when they are above 1: the factored "
        "allowable is met. Fatigue for carbon is half the knocked-down first-ply strength at the 1.6 g "
        "walking stress. Fatigue for a PAHT stay is 0.3 of the knocked-down tensile strength.",
        "",
        f"### {winner['name']} by case",
        "",
        "| case | SF/req | where |",
        "|---|---:|---|",
    ]
    for name, sf in winner["cases"].items():
        lines.append(f"| {name} | {sf:.2f} | {winner['where'][name]} |")
    lines += [
        "",
        "## Why the others lose",
        "",
    ]
    for r in rows:
        if r is winner:
            continue
        lines.append(f"- **{r['name']}.** {r['note']} Pack {r['pack_lb']:.2f} lb, "
                     f"SF/req {r['sf_min']:.2f}, fatigue {r['sf_fatigue']:.2f}.")
    lines += [
        "",
        "## Cost (production frame)",
        "",
        "| item | USD |",
        "|---|---:|",
    ]
    for r in cost["rows"]:
        lines.append(f"| {r['item']} | {r['usd']:.2f} |")
    lines.append(f"| QI carbon spreader, 2.0 mm | {cost['spreader']:.2f} |")
    lines.append(f"| XLPE rails | {cost['foam']:.2f} |")
    lines.append(f"| **total** | **{cost['total']:.2f}** |")
    lines += [
        "",
        "Tube price starts at the `cfrp_rollwrapped_tube` record, $30/m at about 16 mm, and scales with "
        "diameter. That is an estimate, not a quote. The wrap kit, boots, bushings and the Ti mount are "
        "marked ASSUMPTION. Print time is the 44 g rack at 8 mm³/s.",
        "",
        "## Screenshots",
        "",
    ]
    for s in screens:
        lines.append(f"- `{s}`")
    lines += [
        "",
        "## Assumptions still in force",
        "",
        "- Bone end is 20 % of 68 kg on a 22 mm patch. The spreader thickness hangs on it.",
        "- 5.36 lb is not 5.0 lb. The gap is real.",
        "- Small printed parts (rack, pawl, guides) stay PAHT-CF. The stays are not printed.",
        "- The pawl pin runs side to side.",
        "- Lumpy-gear corner is 8 kg on 40 mm.",
        "- MMA bond shear stays 6 MPa hot/wet until the T6 coupons exist. The tube-frame joint screen is above 1; the coupon still governs the release.",
        "- PAHT fatigue ratio 0.3 and the carbon half-strength fatigue screen are the study assumptions, not a measured S-N curve for this layup.",
        "",
    ]
    path = ANALYSIS / "mass_cut.md"
    path.write_text("\n".join(lines))
    return str(path)


def run(log=print):
    log("comfort")
    sheet = comfort()
    log(f"  peak {sheet['peak_kpa']:.1f} kPa  sheet {sheet['sheet_g']:.0f} g")
    log("carbon tube, three torsos")
    carbon = carbon_frame()
    log(f"  min SF/req {carbon['sf_min']:.2f} ({carbon['governing']})  fatigue {carbon['sf_fatigue']:.2f}")
    log("PAHT hollow stays")
    paht_fail = paht_stays(26.0, 3.5, carbon["stay_length_mm"])
    paht_ok = paht_stays(28.0, 4.0, carbon["stay_length_mm"])
    log(f"  OD 26 t 3.5  SF {paht_fail['sf_min']:.2f}  fat {paht_fail['sf_fatigue']:.2f}  stays {paht_fail['stay_g']:.0f} g")
    log(f"  OD 28 t 4.0  SF {paht_ok['sf_min']:.2f}  fat {paht_ok['sf_fatigue']:.2f}  stays {paht_ok['stay_g']:.0f} g")
    foam = sheet["foam_delta_g"]
    sheet_g = sheet["sheet_g"]
    cost = tube_cost_usd()
    # spreader, same formula as the shop sheet
    area_m2 = sheet_g / (2.0 * 1550.0)
    spreader_usd = 350.0 * (2.0 / 3.0) * area_m2
    cost["spreader"] = spreader_usd
    cost["foam"] = 3.0  # ASSUMPTION: two XLPE rails
    cost["total"] = cost["tubes_and_frame"] + spreader_usd + cost["foam"]
    skin = fairing_g(carbon["stay_length_mm"])
    # solid ladder, from the comfort pass (voxel SF, not SF/req)
    solid = json.loads((ANALYSIS / "back_comfort_results.json").read_text())
    solid_env = {"sf_min": solid["sf_min"], "sf_fatigue": solid["sf_fatigue"],
                 "governing": solid["governing"], "cases": solid["cases"],
                 "where": {k: "4 mm voxel, smooth ladder" for k in solid["cases"]}}
    rows = [
        _row("Solid PAHT ladder (retired)", "retired", solid["frame_g"], foam, solid_env,
             sheet["peak_kpa"], sheet["spread_mm"], "continuous, but a 34 mm solid stay",
             206.0, 45.7,
             "The current print. Every case passes and it is the heaviest, slowest option."),
        _row("PAHT stays OD 26 × 3.5 mm", "hollow",
             TUBE_FRAME_G - CARBON_STAY_G + paht_fail["stay_g"] + sheet_g, foam, paht_fail,
             sheet["peak_kpa"], sheet["spread_mm"], "round printed tube, smooth",
             cost["total"] - cost["stay_tubes"] + paht_fail["stay_g"] * 1.08 * 0.08,
             print_hours(paht_fail["stay_g"] + RACK_G),
             "Thinner than the stay that passes. Fatigue of the upper stay is under 1."),
        _row("PAHT stays OD 28 × 4 mm", "hollow",
             TUBE_FRAME_G - CARBON_STAY_G + paht_ok["stay_g"] + sheet_g, foam, paht_ok,
             sheet["peak_kpa"], sheet["spread_mm"], "round printed tube, smooth",
             cost["total"] - cost["stay_tubes"] + paht_ok["stay_g"] * 1.08 * 0.08,
             print_hours(paht_ok["stay_g"] + RACK_G),
             "Lightest hollow PAHT stay that clears strength and fatigue. The carbon tubes it replaces weigh 80 g; these weigh more, so the pack goes up."),
        _row("Carbon tubes + 1.2 mm fairing", "fairing",
             TUBE_FRAME_G + sheet_g + skin, foam, carbon,
             sheet["peak_kpa"], sheet["spread_mm"], "printed skin over round tubes",
             cost["total"] + skin * 1.08 * 0.08, print_hours(skin + RACK_G),
             "Same structure as the carbon ladder. The skin is not in the strength check. It adds mass to hide a tube that is already round."),
        _row("Carbon-tube ladder", "tube",
             TUBE_FRAME_G + sheet_g, foam, carbon,
             sheet["peak_kpa"], sheet["spread_mm"], "round stock tubes, wrapped nodes, no voxel steps",
             cost["total"], print_hours(RACK_G),
             "v2 stays, bars, lumbar plate and crown, plus the carbon spreader and the foam rails. "
             "The wrapped nodes and foot boots are the fairing. Nothing extra is printed to imitate the solid ladder."),
    ]
    winner = choose(rows)
    log(f"winner {winner['name']}  pack {winner['pack_lb']:.2f} lb")
    screens = [plot_options(rows, winner)]
    screens.append(plot_views())
    parts = {
        "soft goods": prod.SOFT_GOODS_G,
        "stay-rail foam, net of the old sheet": foam,
        "carbon tubes, lumbar, crown, wraps, hardware": TUBE_FRAME_G,
        "QI carbon spreader": sheet_g,
    }
    screens.append(plot_mass(parts))
    screens.append(plot_fea(winner["cases"], winner["sf_fatigue"]))
    path = write_doc(rows, winner, cost, screens, sheet)
    out = {"winner": winner["name"], "frame_g": winner["frame_g"], "pack_g": winner["pack_g"],
           "pack_lb": winner["pack_lb"], "sf_min": winner["sf_min"], "sf_fatigue": winner["sf_fatigue"],
           "governing": winner["governing"], "cases": winner["cases"], "where": winner["where"],
           "peak_kpa": winner["peak_kpa"], "spread_mm": winner["spread_mm"],
           "cost_usd": cost["total"], "print_h": winner["print_h"],
           "rows": [{k: r[k] for k in ("name", "frame_g", "pack_g", "pack_lb", "sf_min", "sf_fatigue",
                                       "peak_kpa", "spread_mm", "print_h", "cost_usd", "passes", "cases")}
                    for r in rows],
           "screens": screens}
    (ANALYSIS / "mass_cut_results.json").write_text(json.dumps(out, indent=2))
    log(path)
    return out


if __name__ == "__main__":
    run()
