"""Screens for the CORRIE loadout study (matplotlib, phone-readable PNG <= 1.5 MB).

    python designs/pack_5200/concepts/corrie_loadout.py --render

Writes outputs/screens/20261108_loadout_<n>.png:
  1  packing map, 6-day elk (rifle), CORRIE today: side cutaway + aft view, items coloured by access frequency
  2  the same with the recommended set (IMP-1..IMP-5)
  3  mass and volume by category, three trips (two charts, one measure each)
  4  before / after access table (6-day elk) + per-loadout summary
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import corrie as CO  # noqa: E402
import corrie_loadout as L  # noqa: E402

ROOT = L.ROOT
SCREENS = ROOT / "outputs" / "screens"
DATE = "20261108"
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d9d8d3"
# reference categorical palette (dataviz skill references/palette.md), fixed order, never cycled
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FREQ_COL = {f: SERIES[i] for i, f in enumerate(L.FREQ_ORDER)}
FREQ_LBL = {"constant": "constant (many/h)", "hourly": "hourly", "glassing": "each stop / glassing",
            "weather": "weather", "kill": "at the kill", "emergency": "emergency", "daily": "daily",
            "camp": "camp only"}
SHORT = {"binos": "binos", "rangefinder": "LRF", "phone": "phone", "inreach": "inReach", "headlamp": "lamp",
         "batteries": "batt", "power_bank": "power", "spotter_65": "SPOTTER 65", "spotter_85": "SPOTTER 85",
         "spotter_50": "SPOTTER 50", "tripod_light": "TRIPOD", "tripod_heavy": "TRIPOD", "pan_head": "head",
         "glassing_pad": "sit pad", "shelter_mid": "shelter", "shelter_tent2p": "tent", "quilt_20": "quilt",
         "bag_15": "sleeping bag", "pad_nxt": "pad", "cook_kit": "stove", "fuel_100": "fuel",
         "bladder_2L": "BLADDER 2 L", "bottle_1L": "bottle", "filter": "filter", "snacks_today": "snacks",
         "food_day_elk": "FOOD 4.6 kg", "food_day_sheep": "FOOD", "puffy_jacket": "puffy", "puffy_pants": "puffy pants",
         "rain_jacket": "rain jkt", "rain_pants": "rain pants", "mid_layer": "mid layer", "beanie_gloves": "beanie/gl",
         "socks_underwear": "socks", "first_aid": "first aid", "fire_kit": "fire", "toilet_kit": "toilet",
         "kill_kit": "KILL KIT", "game_bags_elk": "game bags", "trekking_poles": "poles", "lunch_today": "lunch",
         "gps": "GPS", "wind_checker": "wind", "base_mid_sheep": "spare tops", "first_aid_light": "first aid",
         "game_bags_small": "game bags", "calls": "calls", "decoy": "decoy"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def _save(fig, n):
    SCREENS.mkdir(parents=True, exist_ok=True)
    p = SCREENS / f"{DATE}_loadout_{n}.png"
    fig.savefig(p, dpi=110, facecolor=SURF)
    plt.close(fig)
    return p


def _outline_side(ax):
    G = L.G
    z, yf, d = G["z"], G["yf"], G["d"]
    ax.fill_betweenx(z, yf, yf + d, color="#f1f0ec", lw=0)
    ax.plot(yf, z, color=INK, lw=2)
    ax.plot(yf + d, z, color=INK, lw=2)
    ax.plot([yf[0], yf[0] + d[0]], [z[0], z[0]], color=INK, lw=2)
    ax.plot(yf + d / 2, z, color=INK2, lw=0.8, ls=(0, (2, 3)))
    # frame stays (wearer side)
    ax.plot(np.asarray(L.BC.stay_y(z)), z, color=INK2, lw=4, alpha=0.35)
    ax.text(float(L.BC.stay_y([60])[0]) - 8, 80, "frame / wearer", rotation=90, ha="right", va="bottom",
            color=INK2, fontsize=9)
    # door on the aft face
    zd = np.array([CO.DOOR["z_lo"], CO.DOOR["z_hinge"]])
    ax.plot([L.y_front(zd[0]) + 6, L.y_front(zd[1]) + 6], zd, color="#6250d6", lw=5, alpha=0.5)
    ax.text(L.y_front(380) + 14, 380, "U-door\nz 110-650", color=INK2, fontsize=9, va="center")
    ax.axhline(G["zc"], color=GRID, lw=0.8)
    ax.text(-60, G["zc"] + 5, "collar seam", fontsize=8, color=INK2)
    for nm, zz in L.BC.STATIONS.items():
        if nm.startswith("im"):
            ax.plot([yf[0] - 30, float(np.interp(zz, z, yf))], [zz, zz], color=INK2, lw=0.6)
            ax.text(yf[0] - 32, zz, nm.upper(), fontsize=8, ha="right", va="center", color=INK2)


def _block(ax, x0, x1, z0, z1, f, label, fs=8):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=FREQ_COL[f], ec=SURF, lw=2, alpha=0.9))
    if z1 - z0 > 16 and label:
        ax.text(0.5 * (x0 + x1), 0.5 * (z0 + z1), label, ha="center", va="center", fontsize=fs, color=INK,
                bbox=dict(boxstyle="round,pad=0.1", fc=SURF, ec="none", alpha=0.75))


def packing_map(res_pack, summ, title, n):
    G = L.G
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 10.5), gridspec_kw={"width_ratios": [1.0, 1.25]})
    fig.patch.set_facecolor(SURF)
    for a in (a1, a2):
        a.set_facecolor(SURF)
        a.set_aspect("equal")
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    _outline_side(a1)
    top = summ["top_z"]
    a1.axhline(max(top, CO.DOOR["z_hinge"]), color=INK, lw=1.2, ls="--")
    a1.text(G["yf"][0] + 2, max(top, 650) + 8, "roll closes here", fontsize=8, color=INK)
    ext = []
    for r in res_pack:
        if r.get("slot"):
            col, z0, z1 = r["slot"]
            yf = float(np.interp(0.5 * (z0 + z1), G["z"], G["yf"]))
            d = float(np.interp(0.5 * (z0 + z1), G["z"], G["d"]))
            x0, x1 = (yf, yf + d / 2) if col == "F" else (yf + d / 2, yf + d)
            _block(a1, x0, x1, z0, z1, r["access"], SHORT.get(r["id"], r["id"]))
        elif r["zone"] in ("hydro_sleeve", "door_pocket"):
            x, y, z = r["pos"]
            h = 120 if r["zone"] == "door_pocket" else 180
            _block(a1, y - 12, y + 12, z - h / 2, z + h / 2, r["access"], "")
            ext.append(r)
        else:
            ext.append(r)
    # top pouch
    pz = max(top, 650) + L.POUCH_ABOVE_TOP
    a1.add_patch(FancyBboxPatch((30, pz - 35), 210, 70, boxstyle="round,pad=2", fc="none", ec=INK, lw=1.5))
    pouch_names = ", ".join(SHORT.get(r["id"], r["id"]) for r in res_pack if r["zone"] == "top_pouch")
    a1.text(135, pz + 44, "top pouch 4.0 L: " + pouch_names, ha="center", fontsize=8.5, color=INK, wrap=True)
    pouch = [r for r in res_pack if r["zone"] == "top_pouch"]
    for i, r in enumerate(pouch):
        w = 210 / max(1, len(pouch))
        a1.add_patch(Rectangle((30 + i * w, pz - 30), w, 60, fc=FREQ_COL[r["access"]], ec=SURF, lw=2))
    # hipbelt
    hip = [r for r in res_pack if r["zone"] in ("hip_L", "hip_R", "bottle_hip", "strap_clip")]
    a1.add_patch(Rectangle((-110, -20), 70, 80, fc="none", ec=INK2, lw=1, ls="--"))
    chest = [r for r in res_pack if r["zone"] == "chest"]
    a1.text(-75, -40, "hipbelt / strap:\n" + "\n".join(SHORT.get(r["id"], r["id"]) for r in hip), ha="center",
            va="top", fontsize=8, color=INK2)
    a1.text(-150, 760, "chest harness\n(not ours):\n" + "\n".join(SHORT.get(r["id"], r["id"]) for r in chest
                                                            if r["id"] != "bino_harness"),
            ha="left", va="top", fontsize=8, color=INK2)
    a1.set_xlim(-160, 360)
    a1.set_ylim(-170, pz + 90)
    a1.set_xlabel("aft of the frame, y mm")
    a1.set_ylabel("height z mm")
    a1.set_title("Side cutaway (frame half | aft half)", fontsize=12, color=INK, loc="left")
    # ---------------- aft view
    z = G["z"]
    a = G["a"]
    a2.fill_betweenx(z, -a, a, color="#f1f0ec", lw=0)
    a2.plot(a, z, color=INK, lw=2)
    a2.plot(-a, z, color=INK, lw=2)
    # door U
    inset, zl, zh, rr = CO.DOOR["inset"], CO.DOOR["z_lo"], CO.DOOR["z_hinge"], CO.DOOR["r"]
    zz = np.linspace(zl + rr, zh, 30)
    xr = np.array([L.a_at(v) - inset for v in zz])
    a2.plot(xr, zz, color="#6250d6", lw=3, alpha=0.6)
    a2.plot(-xr, zz, color="#6250d6", lw=3, alpha=0.6)
    a2.plot([-xr[0] + rr, xr[0] - rr], [zl, zl], color="#6250d6", lw=3, alpha=0.6)
    for r in res_pack:   # aft-column items visible through the door
        if r.get("slot") and r["slot"][0] == "A":
            _, z0, z1 = r["slot"]
            w = L.a_at(0.5 * (z0 + z1)) - 8
            _block(a2, -w, w, z0, z1, r["access"], SHORT.get(r["id"], r["id"]), fs=9)
    dp = [r for r in res_pack if r["zone"] == "door_pocket"]
    if dp:
        a2.add_patch(Rectangle((-150, 320), 300, 260, fc=FREQ_COL["kill"], alpha=0.25, ec=INK, lw=1.5, ls="--",
                               hatch="//"))
        a2.text(0, 595, "door pocket (IMP-4): " + ", ".join(SHORT.get(r["id"], r["id"]) for r in dp),
                ha="center", fontsize=9, color=INK, bbox=dict(fc=SURF, ec="none", alpha=0.85))
    # wings with their items (left wing = wearer's left: on the aft view it shows on the RIGHT)
    for side, zid in ((1, "wing_L"), (-1, "wing_R")):
        xw0 = side * 205
        items = [r for r in res_pack if r["zone"] in (zid, "scope_sleeve_L" if zid == "wing_L" else "x")]
        a2.add_patch(Rectangle((min(xw0, xw0 + side * 120), 150), 120, 450, fc="none", ec=INK, lw=1.5))
        nm = "LEFT wing" if zid == "wing_L" else "RIGHT wing"
        a2.text(xw0 + side * 60, 615, nm, ha="center", fontsize=9, color=INK)
        h = 440 / max(1, len(items))
        for i, r in enumerate(items):
            z0 = 155 + i * h
            x0 = min(xw0 + side * 5, xw0 + side * 115)
            a2.add_patch(Rectangle((x0, z0), 110, h - 4, fc=FREQ_COL[r["access"]], ec=SURF, lw=2))
            lab = SHORT.get(r["id"], r["id"]) + (" (sleeve)" if r["zone"] == "scope_sleeve_L" else "")
            a2.text(x0 + 55, z0 + h / 2, lab, ha="center", va="center", fontsize=8, rotation=90 if h > 120 else 0,
                    color=INK, bbox=dict(boxstyle="round,pad=0.1", fc=SURF, ec="none", alpha=0.75))
    a2.set_xlim(-360, 360)
    a2.set_ylim(-170, pz + 90)
    a2.set_xlabel("x mm (aft view: wearer's left on the right)")
    a2.set_title("Aft view: door, wings (aft-half items shown through the door)", fontsize=12, color=INK, loc="left")
    # legend (identity never colour-alone: every block also carries a text label)
    hs = [Rectangle((0, 0), 1, 1, fc=FREQ_COL[f]) for f in L.FREQ_ORDER]
    fig.legend(hs, [FREQ_LBL[f] for f in L.FREQ_ORDER], loc="lower center", ncol=4, frameon=False, fontsize=10,
               title="access frequency", title_fontsize=10)
    acc = summ["access"]
    fails = sum(len(v["fail"]) for v in acc.values())
    sub = (f"carried {summ['carried_g']/1000:.1f} kg (+ rifle in hands), main bag {summ['main_bag_used_L']:.0f} of "
           f"{summ['main_bag_cap_L']:.0f} L, bag-load CG {summ['cg_geo_mm'][1]:.0f} mm aft geometric / "
           f"{summ['cg_y_rev_c_15in']:.0f} mm with the 15 in sim peel (rev C 205)  |  access misses: {fails}")
    fig.suptitle(title, fontsize=15, color=INK, x=0.02, ha="left", y=0.985, fontweight="bold")
    fig.text(0.02, 0.945, sub, fontsize=10.5, color=INK2)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.91, bottom=0.13, wspace=0.12)
    return _save(fig, n)


def bars(res, n):
    keys = [("day_rifle_today", "Day hunt"), ("elk6_rifle_today", "6-day elk"), ("sheep8_rifle_today", "8-day sheep")]
    cats = ["optics", "shelter", "sleep", "cook", "water", "food", "clothing", "kill_kit", "nav_comms", "safety",
            "poles"]
    names = {"kill_kit": "kill kit", "nav_comms": "nav / comms / power", "safety": "first aid, fire, toilet"}
    fig, axs = plt.subplots(1, 2, figsize=(13, 9), sharey=True)
    fig.patch.set_facecolor(SURF)
    y = np.arange(len(cats))
    hgt = 0.26
    for ax, meas, lab, scale in ((axs[0], "mass_g", "mass, kg", 1e-3), (axs[1], "vol_L", "packed volume, L", 1.0)):
        ax.set_facecolor(SURF)
        for i, (k, nm) in enumerate(keys):
            bc = res["loadouts"][k]["by_cat"]
            v = [bc.get(c, {}).get(meas, 0) * scale for c in cats]
            ax.barh(y + (i - 1) * hgt, v, height=hgt - 0.04, color=SERIES[i], label=nm, edgecolor=SURF, lw=1)
            if i == 2 or i == 1:
                for yy, vv in zip(y, v):
                    if vv > (2.5 if meas == "mass_g" else 6):
                        ax.text(vv + 0.1, yy + (i - 1) * hgt, f"{vv:.1f}", va="center", fontsize=8.5, color=INK2)
        ax.set_xlabel(lab)
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        tot = [sum(res["loadouts"][k]["by_cat"][c][meas] for c in res["loadouts"][k]["by_cat"] if c != "weapon") * scale
               for k, _ in keys]
        ax.set_title(f"{lab.split(',')[0].capitalize()} by category (totals " +
                     " / ".join(f"{t:.1f}" for t in tot) + f" {lab.split(', ')[1]})", fontsize=11.5, color=INK,
                     loc="left")
    axs[0].set_yticks(y)
    axs[0].set_yticklabels([names.get(c, c) for c in cats])
    axs[0].invert_yaxis()
    axs[0].legend(loc="lower right", frameon=False)
    fig.suptitle("What goes in the bag: three canonical loadouts (worn clothes and the weapon excluded)",
                 fontsize=14, color=INK, x=0.02, ha="left", fontweight="bold")
    fig.text(0.02, 0.925, "Optics are carried on the chest (binos, LRF) and on the pack (spotter, tripod). "
             "Water and food dominate the heavy end; sleep + shelter dominate volume.", fontsize=10.5, color=INK2)
    fig.subplots_adjust(left=0.17, right=0.98, top=0.88, bottom=0.08, wspace=0.08)
    return _save(fig, n)


def access_table(res, n):
    key = "elk6_rifle"
    before = {r["id"]: r for r in res["packs"][f"{key}_today"]}
    after = {r["id"]: r for r in res["packs"][f"{key}_after"]}
    ids = [i for i in before if before[i]["zone"] not in ("hands",)]
    ids.sort(key=lambda i: (L.FREQ_ORDER.index(before[i]["access"]), i))
    zname = {"chest": "chest harness", "hip_L": "hipbelt L", "hip_R": "hipbelt R", "strap_clip": "strap clip",
             "top_pouch": "top pouch", "wing_L": "left wing", "wing_R": "right wing", "scope_sleeve_L": "scope sleeve",
             "hydro_sleeve": "hydration sleeve", "bottle_hip": "bottle holster", "door_pocket": "door pocket"}

    def zn(r):
        z = r["zone"]
        if z.startswith("bag_"):
            col, nm = z.split("_")[1], z.split("_")[2]
            return f"main {'frame' if col == 'F' else 'aft'} {nm}"
        return zname.get(z, z)

    rows = []
    for i in ids:
        b, a = before[i], after[i]
        rows.append([SHORT.get(i, i), FREQ_LBL[b["access"]], zn(b), ("OK " if b["ok"] else "MISS ") + str(b["access_cls"]),
                     zn(a), ("OK " if a["ok"] else "MISS ") + str(a["access_cls"])])
    fig = plt.figure(figsize=(12.5, 13.2))
    fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.02, 0.13, 0.96, 0.80])
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=["item", "access", "zone TODAY", "class", "zone + IMP-1..5", "class"],
                 loc="upper center", cellLoc="left", colWidths=[0.15, 0.2, 0.2, 0.09, 0.2, 0.09])
    t.auto_set_font_size(False)
    t.set_fontsize(10)
    t.scale(1, 1.55)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_text_props(weight="bold", color=INK)
            cell.set_facecolor("#eceae4")
            continue
        txt = cell.get_text().get_text()
        if c in (3, 5):
            cell.set_text_props(weight="bold", color="#b3261e" if txt.startswith("MISS") else "#0b6b0b")
        if c == 1:
            f = before[ids[r - 1]]["access"]
            cell.set_facecolor(FREQ_COL[f] + "40")
    fig.suptitle("Can you reach it? 6-day elk (rifle) in CORRIE, today vs with IMP-1..5", fontsize=15, color=INK,
                 x=0.02, ha="left", fontweight="bold", y=0.985)
    fig.text(0.02, 0.945, "class: 0 on body, 1 pack on, 3 pack off outside, 4 pack off via the door, 5 roll-top / "
             "unpack.  Rule: constant + hourly need <= 1 (pack on); glassing, weather, kill, emergency <= 4 (no roll-top).",
             fontsize=10, color=INK2, wrap=True)
    # per-loadout summary
    lines = []
    for k, nm in (("day_rifle", "Day hunt"), ("elk6_rifle", "6-day elk rifle"), ("elk6_archery", "6-day elk archery"),
                  ("sheep8_rifle", "8-day sheep")):
        out = []
        for cfg in ("today", "after"):
            s = res["loadouts"][f"{k}_{cfg}"]
            miss = [i for v in s["access"].values() for i in v["fail"]]
            out.append(f"{len(miss)} miss" + (f" ({', '.join(SHORT.get(i, i) for i in miss)})" if miss else ""))
        lines.append(f"{nm:18s}  today: {out[0]:60s}  after: {out[1]}")
    fig.text(0.02, 0.105, "All loadouts (access misses):", fontsize=11, color=INK, fontweight="bold")
    fig.text(0.02, 0.025, "\n".join(lines), fontsize=9.5, color=INK2, family="DejaVu Sans Mono")
    return _save(fig, n)


def render_all(res):
    out = [packing_map(res["packs"]["elk6_rifle_today"], res["loadouts"]["elk6_rifle_today"],
                       "CORRIE today, 6-day elk (rifle): where it all goes", 1),
           packing_map(res["packs"]["elk6_rifle_after"], res["loadouts"]["elk6_rifle_after"],
                       "CORRIE + IMP-1..5 (proposal), 6-day elk (rifle)", 2),
           bars(res, 3), access_table(res, 4)]
    return [(str(p), round(Path(p).stat().st_size / 1e6, 2)) for p in out]
