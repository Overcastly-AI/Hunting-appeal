"""Generative printed frame: a smooth branching body, not the solid ladder and not a tube frame.

The visible frame is one printed PAHT-CF part. Stays split into an outer sleeve limb and an
inboard branch, tied back with fillets, with lumbar struts into the hip pivot. Surfaces come
from a smooth distance field (marching cubes, then Taubin), so there are no voxel steps.

The carbon spreader and the XLPE rails stay. A printed plate in their place was already heavier
in the comfort table, and a rib with a gap lets a bone through.

Run: python -m huntkit.gendesign.frame_branch
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.materials import load

from . import frame_production as prod
from . import frame_topopt as ft
from .frame_smooth import choose_back, options

DATE = "20261101"
SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"
G = 9.80665


def _save(fig, name: str) -> str:
    from .render import save
    import shutil
    path = SCREENS / name
    save(fig, path)
    art = Path("/opt/cursor/artifacts/prodframe")
    art.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, art / name)
    out = REPO_ROOT / "outputs" / "screens"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, out / name)
    return str(path)


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / np.maximum(k, 1e-6), 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def _sleeve_y(z):
    return ft.load_envelope().sleeve_y(z)


def _dist_to_segment(p, a, b):
    ab = b - a
    t = np.clip(((p - a) * ab).sum(axis=1) / (np.dot(ab, ab) + 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def stay_radius(z, scale: float = 1.0) -> np.ndarray:
    """Outer radius of the sleeve limb at height z (mm). Matches the branch-frame body."""
    z = np.asarray(z, float)
    r_out = np.interp(z, [0.0, 40.0, 150.0, 190.0, 420.0, 532.0],
                      np.array([10.0, 9.0, 8.5, 13.4, 13.0, 14.0]) * scale)
    r_out = np.maximum(r_out, np.where(z > 160.0, 9.0 + 4.2 * scale, 8.0 * scale))
    # hipbelt-off lands on the upper bar and the pawl. Thicken only that end.
    r_out = np.maximum(r_out, np.where(z > 470.0, 16.0 * scale, 0.0))
    return r_out


def frame_sdf(pts: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Negative inside. ``scale`` multiplies branch radii. The sleeve bore is cut for z > 160."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    yc = np.asarray(_sleeve_y(z), float)
    sdf = np.full(len(pts), 80.0)
    r_out = stay_radius(z, scale)
    for s in (1.0, -1.0):
        stay = np.hypot(x - s * 115.0, y - yc) - r_out
        stay = np.where((z < -2.0) | (z > 540.0), 40.0, stay)
        foot = np.sqrt((x - s * 115.0) ** 2 + (y - yc) ** 2 + (z - 10.0) ** 2) - 12.0 * scale
        stay = _smin(stay, foot, 8.0)
        sdf = _smin(sdf, stay, 7.0)
        # inboard branch: leaves the stay, bows toward the center, rejoins. The generative split.
        t = np.clip((z - 165.0) / 320.0, 0.0, 1.0)
        bow = np.sin(np.pi * t)
        xb = s * (115.0 - 46.0 * bow)
        yb = yc + 6.0 * bow
        branch = np.hypot(x - xb, y - yb) - (6.2 * scale)
        branch = np.where((z < 155.0) | (z > 495.0), 30.0, branch)
        sdf = _smin(sdf, branch, 12.0)
    # lumbar struts, pivot (0, -48, 120) into each stay. Two per side so the pan is a bone, not a slab.
    for s in (1.0, -1.0):
        for z1, y1 in ((78.0, 0.0), (155.0, -4.0)):
            a = np.array([0.0, -42.0, 120.0])
            b = np.array([s * 115.0, float(_sleeve_y(z1)) + y1, z1])
            d = _dist_to_segment(pts, a, b)
            sdf = _smin(sdf, d - 7.5 * scale, 10.0)
    # cross bars where the meat straps land, round, filleted into the limbs
    for zc, rad in ((330.0, 6.5 * scale), (508.0, 11.0 * scale)):
        bar = np.sqrt((y - float(_sleeve_y(zc))) ** 2 + (z - zc) ** 2) - rad
        bar = np.where(np.abs(x) > 118.0, 30.0, bar)
        sdf = _smin(sdf, bar, 9.0)
    # pawl housing bulge, so the cheek is not a one-voxel stub on the bar
    yp = float(_sleeve_y(512.0))
    pawl = np.sqrt(x ** 2 + (y - yp + 6.0) ** 2 + (z - 512.0) ** 2) - 16.0 * scale
    sdf = _smin(sdf, pawl, 8.0)
    # bag fairleads: added on the bag face only. Bore cut below still owns the sleeve.
    from .bag_attach import attachment_field
    sdf = _smin(sdf, attachment_field(pts, scale), 4.5)
    # sleeve bores. Wall outside the bore is at least 4.2 mm * scale (two voxels on a 2 mm mesh).
    for s in (1.0, -1.0):
        r = np.hypot(x - s * 115.0, y - yc)
        tool = np.where((z > 160.0) & (z < 546.0), r - 9.0, 80.0)
        sdf = np.maximum(sdf, -tool)
    # spine channel so the crown rack still fits
    ch = (np.abs(x) < 16.0) & (np.abs((y - yc) + 18.0) < 9.0) & (z > 300.0)
    sdf = np.where(ch, np.maximum(sdf, 2.0), sdf)
    return sdf


def raster_solid(scale: float, h: float):
    dom = ft.build_domain(h, sleeve_wall=max(4.2 * scale, h))
    sdf = frame_sdf(dom.grid.elem_centers(), scale=scale)
    solid = (sdf <= 0.0) | dom.passive_solid
    solid &= ~dom.passive_void
    return dom, solid


def solid_mass_g(solid, h, rho=1060.0) -> float:
    return float(solid.sum() * h ** 3 * rho / 1e6)


def mesh_from_sdf(scale: float, h: float = 2.0):
    from skimage.measure import marching_cubes
    import trimesh
    x0 = np.array([-150.0, -52.0, -2.0])
    dims = np.array([300.0, 78.0, 548.0])
    n = np.maximum((dims / h).astype(int), 2)
    axes = [x0[i] + np.arange(n[i]) * h for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    sdf = frame_sdf(np.c_[X.ravel(), Y.ravel(), Z.ravel()], scale=scale).reshape(X.shape)
    verts, faces, _, _ = marching_cubes(sdf, level=0.0, spacing=(h, h, h))
    mesh = trimesh.Trimesh(verts + x0, faces, process=False)
    trimesh.smoothing.filter_taubin(mesh, lamb=0.45, nu=-0.45, iterations=8)
    mesh.remove_unreferenced_vertices()
    return mesh


def web_comfort() -> dict:
    """Could the printed body itself be the spreader? Use the same plate model as the comfort pass."""
    rows = options()
    carbon = choose_back(rows)
    paht = [r for r in rows if r["name"].startswith("PAHT web") and r["passes"]]
    light_paht = min(paht, key=lambda r: r["mass_g"]) if paht else None
    return {"carbon": carbon, "printed_plate": light_paht}


def pack_numbers(body_g: float, sheet_g: float, foam_delta: float) -> dict:
    from .frame_eval import kept_g
    # dowels are gone: one printed body, no segment joint. Pawl bushings stay.
    pawl = 9.94
    inserts = 12.0
    frame = body_g + sheet_g + float(kept_g()) + pawl + inserts
    pack = prod.SOFT_GOODS_G + foam_delta + frame
    return {"frame_g": frame, "pack_g": pack, "pack_lb": pack / 453.59237,
            "kept_g": float(kept_g()), "pawl_g": pawl, "inserts_g": inserts}


def plot_options(rows, winner) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S2, S3
    _style()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for r in rows:
        ax.scatter(r["pack_lb"], r["sf_min"], s=90, c=(S3 if r["passes"] else "#b0aea8"), zorder=3)
        ax.annotate(r["short"], (r["pack_lb"], r["sf_min"]), textcoords="offset points",
                    xytext=r.get("xy", (6, 6)), fontsize=8)
    ax.scatter([winner["pack_lb"]], [winner["sf_min"]], s=200, facecolors="none", edgecolors="black", lw=1.3)
    ax.axhline(1.0, color=S2, ls="--", lw=1.0)
    ax.axvline(5.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("pack mass (lb)")
    ax.set_ylabel("minimum safety factor")
    ax.set_title("Generative frame options", loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_gen_1_options.png")


def plot_mass(parts: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1
    _style()
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    names = list(parts)
    vals = [parts[n] for n in names]
    ax.barh(names, vals, color=S1)
    for i, v in enumerate(vals):
        ax.text(v + 6, i, f"{v:.0f} g", va="center", fontsize=8)
    ax.set_xlabel("grams")
    ax.set_title("Where the grams are", loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_gen_3_mass.png")


def plot_fea(cases: dict, fatigue: float) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1
    _style()
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    names = list(cases)
    vals = [cases[n] for n in names]
    colors = ["#1baf7a" if v >= 1.3 else "#eda100" if v >= 1.0 else "#d6342a" for v in vals]
    ax.barh(names, vals, color=colors)
    ax.axvline(1.0, color=S1, ls="--", lw=1.0)
    ax.set_xlabel("safety factor, fine mesh, worst torso")
    ax.set_title(f"Branch frame  ·  min {min(vals):.2f}  ·  fatigue {fatigue:.2f}",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_gen_4_fea.png")


def plot_views(mesh) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .frame_render import autocrop, raster, simplify
    from .render import _style, SURF
    _style()
    m = simplify(mesh, target=22000)
    fig = plt.figure(figsize=(11.2, 4.8))
    views = (("bag side", 16, 28), ("wearer side", 12, 200), ("side", 4, 90), ("top", 78, 20))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 4, i + 1)
        img, info = raster([(m, (0.28, 0.30, 0.33))], el, az, size=360, spec=0.22)
        ax.imshow(autocrop(img, info["mask"], pad=6))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Generative branch frame, smooth printed body", x=0.02, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.patch.set_facecolor(SURF)
    return _save(fig, f"{DATE}_gen_2_views.png")


def write_doc(text: str) -> str:
    path = ANALYSIS / "generative_branch.md"
    path.write_text(text)
    return str(path)


def run(log=print):
    log("comfort (spreader stays the carbon sheet)")
    comfort = web_comfort()
    carbon = comfort["carbon"]
    plate = comfort["printed_plate"]
    foam_delta = max(carbon["foam_g"] - 11.5, 0.0)
    log(f"  carbon sheet {carbon['sheet_g']:.0f} g  peak {carbon['peak_kpa']:.1f}")
    if plate:
        log(f"  lightest printed plate that passes comfort: {plate['name']}  {plate['mass_g']:.0f} g")

    log("branch body, 2 mm release check")
    # scale 1.00 clears strength (hipbelt SF 1.39 with the upper-bar bulge) and misses
    # fatigue at 0.94. 1.05 is the next step. 1.12 was heavier than the fatigue gap needs.
    scale = 1.05
    sets = ft.beam_loadsets(log=log)
    use = None
    body_g = None
    for attempt, scale in enumerate((1.05, 1.08)):
        log(f"fine 2 mm check, scale {scale:.2f}")
        dom2, solid2 = raster_solid(scale, 2.0)
        body_g = solid_mass_g(solid2, 2.0)
        use = prod.verify_solid(dom2, solid2, sets)
        log(f"  2 mm body {body_g:.0f} g  minSF {use['sf_strength_min']:.2f}  fat {use['sf_fatigue']:.2f}  "
            f"({use['governing']})")
        if use["sf_strength_min"] >= 1.0 and use["sf_fatigue"] >= 1.0 and use["sf_creep_rupture"] >= 1.0:
            break
    mass = pack_numbers(body_g, carbon["sheet_g"], foam_delta)

    log("surface")
    mesh = mesh_from_sdf(scale, h=2.2)
    mesh.export(PRINT / "genframe_assembled.stl")
    # keep the carbon spreader mesh already written; refresh its label
    (PRINT / "genframe_barrier.json").write_text(json.dumps({
        "material": "carbon",
        "label": "QI carbon 2.0 mm spreader, behind the branching frame"}))

    by = {}
    for c in use["cases"]:
        by[c["case"]] = min(by.get(c["case"], 99.0), c["sf"])
    passes = use["sf_strength_min"] >= 1.0 and use["sf_fatigue"] >= 1.0 and carbon["peak_kpa"] <= 14.0
    branch_row = {
        "name": "Branch frame + carbon spreader",
        "short": "branch frame",
        "xy": (-78, 10),
        "frame_g": mass["frame_g"], "pack_g": mass["pack_g"], "pack_lb": mass["pack_lb"],
        "sf_min": use["sf_strength_min"], "sf_fatigue": use["sf_fatigue"],
        "sf_creep": use["sf_creep_rupture"], "governing": use["governing"],
        "cases": by, "peak_kpa": carbon["peak_kpa"], "spread_mm": carbon["spread_mm"],
        "print_h": prod.print_hours(body_g / 1.060 * 1000.0),
        "passes": passes, "body_g": body_g, "scale": scale,
    }
    # print_hours expects mm^3. body_g / 1.060 is cm^3 if density is g/cm^3. 1.060 g/cm^3.
    # prod.print_hours(volume_mm3). volume_mm3 = body_g / 0.001060
    branch_row["print_h"] = prod.print_hours(body_g / 0.001060)

    solid = json.loads((ANALYSIS / "back_comfort_results.json").read_text())
    tube = json.loads((ANALYSIS / "mass_cut_results.json").read_text())
    tube_row = next(r for r in tube["rows"] if r["name"] == "Carbon-tube ladder")
    rows = [
        {"name": "Solid PAHT ladder", "short": "solid ladder", "xy": (-4, 8),
         "frame_g": solid["frame_g"], "pack_lb": solid["pack_lb"], "sf_min": solid["sf_min"],
         "sf_fatigue": solid["sf_fatigue"], "peak_kpa": carbon["peak_kpa"], "spread_mm": carbon["spread_mm"],
         "print_h": 45.7, "cost_usd": 206.0, "passes": True, "cases": solid["cases"],
         "look": "smooth, but a fat ladder, not branching"},
        {"name": "Carbon-tube ladder (rejected)", "short": "tube ladder", "xy": (8, -12),
         "frame_g": tube_row["frame_g"], "pack_lb": tube_row["pack_lb"], "sf_min": tube_row["sf_min"],
         "sf_fatigue": tube_row["sf_fatigue"], "peak_kpa": carbon["peak_kpa"], "spread_mm": carbon["spread_mm"],
         "print_h": tube_row["print_h"], "cost_usd": tube_row["cost_usd"], "passes": False,
         "cases": tube_row["cases"],
         "look": "round tubes. Owner rejected it: the product has to read as a printed generative frame"},
        branch_row | {"look": "one printed part, split stays, lumbar struts, smooth distance-field surface",
                      "cost_usd": None},
    ]
    if plate:
        # printed plate instead of the carbon sheet: add the plate, drop the carbon sheet, keep a branch body
        # that still has to exist. Use this branch body with the plate's added mass in place of the sheet.
        plate_frame = mass["frame_g"] - carbon["sheet_g"] + plate["sheet_g"]
        plate_pack = prod.SOFT_GOODS_G + foam_delta + plate_frame
        rows.append({
            "name": plate["name"], "short": "printed plate", "xy": (10, -14),
            "frame_g": plate_frame, "pack_lb": plate_pack / 453.59237,
            "sf_min": use["sf_strength_min"], "sf_fatigue": use["sf_fatigue"],
            "peak_kpa": plate["peak_kpa"], "spread_mm": plate["spread_mm"],
            "print_h": branch_row["print_h"] + prod.print_hours(plate["sheet_g"] / 0.001060),
            "passes": plate["passes"] and passes, "cases": by,
            "look": "flat printed plate across the window. Passes comfort and weighs more than the carbon sheet",
        })

    # cost of the branch frame: filament + spreader + kept hardware allowances from the tube sheet's small parts
    pa = load("pa12_cf_fdm_paht")
    price = float(pa.require("print_cost_usd_per_g"))
    filament = body_g * 1.08 * price
    scrap = filament * 0.15
    machine = branch_row["print_h"] * 1.0
    area_m2 = carbon["sheet_g"] / (2.0 * 1550.0)
    spreader_usd = 350.0 * (2.0 / 3.0) * area_m2
    # crown tubes are still bought. Lengths from frame.yaml, $30/m at 16 mm scaled by diameter.
    crown_usd = 30.0 * (0.860 + 0.214 * 18 / 16 + 0.300 * 20 / 16)
    other = 35.0 + 8.0 + 5.0 + 2.0 + 3.0  # Ti, boots not used, bushings, MMA, foam. Boots are printed now.
    # foot is printed. Drop the $8 boot assumption. Ti mount, bushings, MMA, foam rails.
    other = 35.0 + 5.0 + 2.0 + 3.0
    cost = filament + scrap + machine + spreader_usd + crown_usd + other
    branch_row["cost_usd"] = cost

    screens = [
        plot_options(rows, branch_row),
        plot_views(mesh),
        plot_mass({
            "soft goods": prod.SOFT_GOODS_G,
            "stay-rail foam, net": foam_delta,
            "printed branch body": body_g,
            "carbon crown, rack, Ti, bushings": mass["kept_g"],
            "QI carbon spreader": carbon["sheet_g"],
            "pawl bushings and inserts": mass["pawl_g"] + mass["inserts_g"],
        }),
        plot_fea(by, use["sf_fatigue"]),
    ]
    gap = mass["pack_g"] - 2268.0
    lines = [
        "# Generative branch frame",
        "",
        "The production frame is printed again. The carbon-tube ladder is not the product. "
        "Code: `huntkit/gendesign/frame_branch.py`.",
        "",
        "## Recommendation",
        "",
        "One **PAHT-CF branching body**. Each stay splits into the sleeve limb and an inboard branch, "
        "filleted back together. Lumbar struts run from the hip pivot into the stays. The surface is a "
        "smooth distance field, not a voxel lattice.",
        "",
        f"- Printed body **{body_g:.0f} g**. Frame **{mass['frame_g']:.0f} g**. "
        f"Pack **{mass['pack_g']:.0f} g ({mass['pack_lb']:.2f} lb)**.",
        f"- Fine check is the **2 mm** mesh (a 4 mm wall is two elements, not a one-voxel skin). "
        f"Minimum SF **{use['sf_strength_min']:.2f}** ({use['governing']}). "
        f"Fatigue **{use['sf_fatigue']:.2f}**. Creep-rupture **{use['sf_creep_rupture']:.2f}**.",
        f"- Comfort unchanged: carbon spreader, peak **{carbon['peak_kpa']:.1f} kPa**, "
        f"spread **{carbon['spread_mm']:.0f} mm**.",
        f"- Print time about **{branch_row['print_h']:.0f} h**. Material cost about **${cost:.0f}**.",
        "",
        f"5.0 lb is missed by **{gap:.0f} g**. The floor under this architecture is the soft goods "
        "(1655 g), the carbon crown and rack (205 g), the spreader (193 g) and a printed sleeve that "
        "has to wrap an 18 mm bore. Those four lines already sit on the target before the branches and "
        "the lumbar struts. Closing the gap means a lighter spreader that still meets 14 kPa, or a "
        "lighter crown, not a thinner stay skin.",
        "",
        "## Why this and not the others",
        "",
        "- The solid ladder passes and looks smooth, and it is 1734 g because the stays are ~34 mm across.",
        "- The tube ladder is lighter and was rejected. The frame has to read as a generative print.",
        "- A printed plate can replace the carbon spreader. The lightest one that still spreads a bone "
        f"is {plate['name'] if plate else 'none'}, at {plate['mass_g']:.0f} g added versus "
        f"{carbon['sheet_g']:.0f} g for the carbon sheet. It is the heavier comfort part." if plate else
        "- No printed plate passed the comfort check.",
        "- A gyroid core inside a thick stay does not remove the wall that carries bending, and it "
        "reads as fill, not as a branch. It was not used.",
        "- Annealing does not change density. PPA-CF is stiffer when hot and about 18 % denser, so it "
        "is not a mass path. The filament stays PAHT-CF.",
        "- A carbon liner inside the sleeve was looked at. The crown leg already fills the 18 mm bore, "
        "so a liner only thickens that wall. It does not remove the printed socket.",
        "",
        "## Safety factors (2 mm, worst torso)",
        "",
        "| case | SF |",
        "|---|---:|",
    ]
    for name, sf in by.items():
        lines.append(f"| {name} | {sf:.2f} |")
    lines += [
        "",
        f"Fatigue SF **{use['sf_fatigue']:.2f}**. Creep-rupture SF **{use['sf_creep_rupture']:.2f}**.",
        "",
        "## Options",
        "",
        "| option | frame g | pack lb | min SF | fatigue | peak kPa | spread mm | print h | pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['frame_g']:.0f} | {r['pack_lb']:.2f} | {r['sf_min']:.2f} | "
            f"{r['sf_fatigue']:.2f} | {r['peak_kpa']:.1f} | {r['spread_mm']:.0f} | {r['print_h']:.1f} | "
            f"{'yes' if r['passes'] else 'no'} |"
        )
    lines += ["", "## Screenshots", ""]
    for s in screens:
        lines.append(f"- `{s}`")
    lines += [
        "",
        "## Assumptions",
        "",
        "- Bone end is 20 % of 68 kg on a 22 mm patch. The carbon spreader hangs on it.",
        "- The crown stays the carbon telescoping crown. A printed crown was already rejected on creep and stiffness.",
        "- Pawl pin runs side to side. The 304 sleeve in the cheek still stands.",
        "- No segment joint: the body is printed as two pieces only if the slicer has to split it. The check is of the whole body.",
        "- Fatigue ratio 0.3 and the 0.8 hot/wet knockdown are the PAHT study assumptions.",
        "",
    ]
    path = write_doc("\n".join(lines))
    out = {
        "winner": branch_row["name"], "body_g": body_g, "frame_g": mass["frame_g"],
        "pack_g": mass["pack_g"], "pack_lb": mass["pack_lb"], "scale": scale,
        "sf_min": use["sf_strength_min"], "sf_fatigue": use["sf_fatigue"],
        "sf_creep": use["sf_creep_rupture"], "governing": use["governing"],
        "cases": by, "peak_kpa": carbon["peak_kpa"], "spread_mm": carbon["spread_mm"],
        "print_h": branch_row["print_h"], "cost_usd": cost, "h_mm": 2.0,
        "screens": screens,
    }
    (ANALYSIS / "generative_branch_results.json").write_text(json.dumps(out, indent=2))
    log(path)
    return out


if __name__ == "__main__":
    run()
