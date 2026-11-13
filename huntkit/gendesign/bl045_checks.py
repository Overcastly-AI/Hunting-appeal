"""BL-045: crown tube with the B-25 mitre, spine clamp, IM / US fairlead clearance, the loose island, stale records.

Collects the five items into one record, ``designs/pack_5200/analysis/crown_and_fairlead_checks.md`` (+ ``.json``) and
the screenshots. The engineering lives in the modules each item belongs to:

1. crown tube: ``crown_tube_guy_loop.b25_topology_recheck`` (ring check on the real B-25 bearing and pull directions);
2. spine clamp: ``crown_spine_clamp`` (frame-model joint loads, sizing, H1 STL geometry, B-25 clearances, constants);
3. IM / US fairleads: ``bag_attach.PIN_WRAP / eye_geom / imus_eye_envelope`` (what wraps each pin; the hinge's eye
   clearance on all ten) and :func:`imus_strength` here (cheek FEA before / after, rev C and sim loads, pin bending);
   print files re-exported by ``h1_buckling.export_print`` and slice-checked by ``h1_fairleads.check_stl``;
4. loose island: ``frame_h1.print_mesh`` (BOSS_CORE_MM), shown here before / after;
5. stale records: ``rev_c_verification.refresh_attachments``, ``h1_buckling`` keep-outs, ``frame_fixed`` label.

    python -m huntkit.gendesign.bl045_checks
"""
from __future__ import annotations

import dataclasses
import json
import math
import subprocess
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
ANALYSIS = REPO / "designs" / "pack_5200" / "analysis"
DOC = ANALYSIS / "crown_and_fairlead_checks.md"
RESULTS = ANALYSIS / "crown_and_fairlead_checks.json"
OUT = REPO / "outputs" / "bl045"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL045_"
OLD_COMMIT = "5c54df9"        # HEAD before BL-045 (BL-043): the print files with the island and the 1.9 mm gaps
G_WALK, FACTOR = 1.6, 3.0     # HA-LS-1 rev C fatigue peak; sim 1 g -> factored (2.0 g x 1.5), BL-021 SIM_BODY


# ===================================================================================== item 3: IM / US strength
def station_loads() -> dict:
    """Rev C governing factored vector per IM station (rev_c_verification gov_c, both couple variants) and the US
    cradle (loadpath_verification S5-S7: 720 N factored at 1.6 g x 1.5 along the strap; direction from
    meat_haul._theta, aft and down). Sim 1 g vectors for IM3 (im3_body_simloads, hook_im520 R/L, mirrored)."""
    from . import meat_haul as MH
    gov = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]
    th = MH._theta()
    T = 720.0
    out = {k: {"vec": [gov[k].get("fx", 0.0), gov[k]["fy"], gov[k]["fz"]], "g_times_req": gov[k]["g_times_req"],
               "case": gov[k]["case"], "source": "rev_c_verification gov_c"} for k in ("im1", "im2", "im3")}
    for k in ("us1", "us2"):
        out[k] = {"vec": [0.0, T * math.cos(th), -T * math.sin(th)], "g_times_req": 2.4,
                  "case": "US cradle, 53 kg float limit (loadpath S5-S7)",
                  "source": f"loadpath_verification S6 720 N; direction meat_haul._theta {math.degrees(th):.1f} deg"}
    sims = {}
    p = REPO / "outputs" / "im3_body_simloads" / "sim_frame_forces_rev1.json"
    if p.exists():
        for run, v in json.loads(p.read_text()).items():
            for side in "RL":
                f = np.asarray(v["forces"][f"hook_im520_{side}"]["f"], float)
                if side == "L":
                    f[0] = -f[0]
                sims[f"{run}|{side}"] = f.tolist()
    out["im3"]["sim_1g"] = sims
    return out


def imus_strength(h: float = 1.0, log=print) -> dict:
    """Cheek FEA (h1_fairleads.fairlead_fea, 1 mm voxels; the crown bore empty on the sleeve stations) on the BL-042
    print geometry and on the BL-045 eye geometry, per IM / US station; pin bending (h1_fairleads.pin_bending)."""
    from . import bag_attach as BA
    from . import h1_fairleads as HF
    from .frame_branch import stay_radius
    pa = BA._paht()
    L = station_loads()
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for st in BA.IMUS_STATIONS:
        z = BA.IMUS_Z[st]
        r = float(stay_radius(z, BA.SCALE))
        bore = BA.SLEEVE_BORE_R_REAM if z + 9.0 + 4.0 > BA.SLEEVE_BORE_FROM_Z else None
        lo = L[st]
        loads = {"revC": lo["vec"]}
        for k, v in lo.get("sim_1g", {}).items():
            loads[k] = (1000.0 * np.asarray(v) / np.linalg.norm(v)).tolist()
        row = {"z": z, "stay_r": r, "bore_r": bore, "load": {k: v for k, v in lo.items() if k != "sim_1g"}}
        for tag, g in (("bl042", HF.bl042_geom_of(st)), ("bl045", HF.station_geom(st))):
            cp = OUT / f"fea_{st}_{tag}_{h:g}.json"
            key = {"geom": dataclasses.asdict(g), "bore": bore, "loads": loads}
            if cp.exists() and json.loads(cp.read_text()).get("key") == json.loads(json.dumps(key)):
                f = json.loads(cp.read_text())
            else:
                f = HF.fairlead_fea(g, r, loads, h=h, bore_r=bore)
                f["key"] = key
                cp.write_text(json.dumps(f))
            rc = f["loads"]["revC"]
            gr = lo["g_times_req"]
            d = {"gap_under_pin_mm": round(g.gap_under_pin, 2), "throat_mm": g.throat, "root_depth_mm": g.embed,
                 "added_g": round(f["added_g"], 2), "force_n": round(rc["force_n"], 1), "sf": round(rc["sf"], 2),
                 "fatigue": round(BA._fatigue_sf(rc["fi99"], gr, pa["fat"]), 2),
                 "creep": round(BA._creep_sf(rc["fi99"], gr, pa["rupture"]), 2),
                 "pin": {k: round(v, 2) for k, v in HF.pin_bending(rc["force_n"], g.throat, g.cheek, g.pin_d, gr).items()}}
            sims = lo.get("sim_1g", {})
            if sims:
                worst = None
                for k, v in sims.items():
                    mag = float(np.linalg.norm(v))
                    fpn = f["loads"][k]["fi99"] / 1000.0
                    s = {"run": k, "f1g_n": round(mag, 1), "strength": round(1.0 / (fpn * FACTOR * mag), 2),
                         "fatigue": round(pa["fat"] / (fpn * G_WALK * mag), 2), "creep": round(pa["rupture"] / (fpn * mag), 2)}
                    if worst is None or s["fatigue"] < worst["fatigue"]:
                        worst = s
                d["sim_worst"] = worst
                fmax = max(float(np.linalg.norm(v)) for v in sims.values())
                d["pin_sim"] = {k: round(v, 2) for k, v in
                                HF.pin_bending(FACTOR * fmax, g.throat, g.cheek, g.pin_d, FACTOR).items()}
            row[tag] = d
        res[st] = row
        if log:
            log(f"  {st}: SF {row['bl042']['sf']} -> {row['bl045']['sf']}, fatigue {row['bl042']['fatigue']} -> "
                f"{row['bl045']['fatigue']}")
    return res


# ===================================================================================== item 4: island
def island(log=print) -> dict:
    """The lower-half split of the print before BL-045 (git OLD_COMMIT) and now: shells, dropped piece, where."""
    import trimesh
    from . import h1_buckling as B
    from .frame_topopt import split_mesh
    OUT.mkdir(parents=True, exist_ok=True)
    old = OUT / "h1_assembled_before_bl045.stl"
    if not old.exists():
        old.write_bytes(subprocess.run(["git", "show", f"{OLD_COMMIT}:designs/pack_5200/print/frame_h1/h1_assembled.stl"],
                                       cwd=REPO, capture_output=True, check=True).stdout)
    out = {}
    for tag, path in (("before", old), ("after", REPO / "designs/pack_5200/print/frame_h1/h1_assembled.stl")):
        m = trimesh.load(path)
        lo, hi = split_mesh(m, 234.0)
        parts = sorted(lo.split(only_watertight=False), key=lambda p: -p.volume)
        out[tag] = {"assembled_g": round(m.volume * 1.06e-3, 1), "lower_shells": len(parts),
                    "lower_g": round(parts[0].volume * 1.06e-3, 1),
                    "islands": [{"mm3": round(p.volume, 1), "centre": [round(float(c), 1) for c in p.bounds.mean(0)],
                                 "bounds": np.round(p.bounds, 1).tolist()} for p in parts[1:]],
                    "lost_in_split_mm3": round(m.volume - lo.volume - hi.volume + sum(p.volume for p in parts[1:]), 1)}
    return out


# ===================================================================================== figures
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def fig_crown(crown: dict, clamp: dict, geo: dict, b25: dict, path: Path) -> str:
    """Crown at kit S 15 in, seen from the bag, to scale: bar, real clamp, spine, real pawl housing / upper body, and
    B-25 (sleeve, drop, mitre, necked run, spine wrap); right: the bar's ring SF on each basis."""
    plt = _plt()
    from matplotlib.patches import Polygon, Rectangle
    from . import crown_diet as CDI
    fig = plt.figure(figsize=(13.5, 6.6), dpi=100)
    ax = fig.add_axes([0.07, 0.10, 0.54, 0.78])
    rb, rs = 9.0, 10.0
    kS = b25["kits"]["S"]
    uz = CDI.geom()["uz"]
    zb = kS["bar_z"]
    s_of = lambda z: (zb - z) / uz       # noqa: E731
    ax.add_patch(Rectangle((-112, -rb), 224, 2 * rb, fc="#cfcfcf", ec="#333", lw=1))
    sh = s_of(geo["pawl_housing_top_z"])
    ax.add_patch(Rectangle((-rs, -sh - 12), 2 * rs, sh + 12 - rb, fc="#e2e2e2", ec="#333", lw=0.8))
    hw = geo["pawl_housing_half_w_mm"]
    ax.add_patch(Rectangle((-hw, -s_of(500.0)), 2 * hw, s_of(500.0) - sh, fc="#d9c7a0", ec="#7a5c1e", alpha=0.8))
    sb = s_of(geo["body_top_z_in_b25_band"])
    for sx in (-1, 1):
        a, b = sorted((sx * hw, sx * 112))
        ax.add_patch(Rectangle((a, -s_of(495.0)), b - a, s_of(495.0) - sb, fc="#e8e0cc", ec="#7a5c1e", alpha=0.7))
    ax.text(0, -sh - 4, f"pawl housing (H1 STL)\ntop {geo['pawl_housing_up_mm']:.1f} above\nthe pawl line, |x| {hw:.1f}",
            ha="center", va="top", fontsize=7.5, color="#5c4310")
    ch, col = clamp["half_x_mm"], clamp["collar_below_bar_underside_mm"]
    ax.add_patch(Rectangle((-ch, -rb - 0.8), 2 * ch, 2 * rb + 1.6, fc="#7d93b0", ec="#223", alpha=0.85))
    so = clamp["socket_od_mm"] / 2
    ax.add_patch(Rectangle((-so, -rb - col), 2 * so, col, fc="#7d93b0", ec="#223", alpha=0.85))
    ax.text(-100, rb + 6, f"spine clamp (7075, bonded): {2 * ch:.0f} mm along the bar, collar {col:.1f} mm",
            ha="left", fontsize=8.5, color="#223")
    from .crown_spine_clamp import B25_BAND
    x0, x1 = B25_BAND
    st = b25["run_top_s_mm"]
    for sx in (-1, 1):
        a, b = sorted((sx * x0, sx * x1))
        ax.add_patch(Rectangle((a, -rb), b - a, 2 * rb, fc="#e9b96e", ec="#a5650a", alpha=0.95))
        ax.add_patch(Rectangle((a, -st), b - a, st - rb, fc="#e9b96e", ec="#a5650a", alpha=0.45))
        xi, xo = sx * x0, sx * x1
        ax.add_patch(Polygon([(xo, -st), (xo, -st - 38), (xi, -st - 38)], fc="#e9b96e", ec="#a5650a", alpha=0.7))
        ax.add_patch(Rectangle((min(sx * (rs + 1.2), xi), -st - 25), abs(xi - sx * (rs + 1.2)), 25,
                               fc="#e9b96e", ec="#a5650a", alpha=0.7))
    ax.add_patch(Rectangle((-rs - 1.2, -st - 25), 2 * rs + 2.4, 25, fc="#c27c0e", ec="#a5650a"))
    ax.annotate(f"spine wrap {kS['wrap_to_housing_mm']:.1f} mm\nabove the housing\n(BL-043 assumed 13)",
                (-rs - 1, -st - 25), (-108, -st - 40), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate(f"mitre {kS['mitre_to_body_in_band_mm']:.1f} mm above\nthe printed body", (60, -st - 38),
                (40, -st - 70), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("", (ch, rb + 2.5), (x0, rb + 2.5), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(0.5 * (ch + x0), rb + 3.5, f"{b25['band_to_clamp_x_mm']:.1f}", ha="center", fontsize=8)
    ax.set_xlim(-115, 115)
    ax.set_ylim(-s_of(492.0), 22)
    ax.set_aspect("equal")
    ax.set_xlabel("x along the crown bar (mm)")
    ax.set_ylabel("down the spine from the bar centre (mm)")
    ax.set_title(f"Kit S at {kS['torso_in']:g} in (shortest spine above the pawl), seen from the bag. Real clamp and "
                 "housing; B-25 as SK-12", fontsize=10, loc="left")
    ax2 = fig.add_axes([0.73, 0.16, 0.25, 0.68])
    ck = crown["checks"]
    labs = [("bl041_scalar", "BL-041 sum, 38 mm"), ("vector", "real pull vectors, 38 mm"),
            ("bound", "run tension in line, 38 mm"), ("vector_toggle_width", "vectors, 30 mm (toggle)"),
            ("bound_toggle_width", "in line, 30 mm (toggle)")]
    y = np.arange(len(labs))
    sst = [ck[k]["sf_static"] for k, _ in labs]
    sft = [ck[k]["sf_fatigue"] for k, _ in labs]
    ax2.barh(y + 0.2, sst, 0.38, color="#3d6fb6", label="static (>= 1.0)")
    ax2.barh(y - 0.2, sft, 0.38, color="#d08a2e", label="fatigue (>= 1.0)")
    for i in range(len(labs)):
        ax2.text(sst[i] + 0.02, y[i] + 0.2, f"{sst[i]:.2f}", va="center", fontsize=8)
        ax2.text(sft[i] + 0.02, y[i] - 0.2, f"{sft[i]:.2f}", va="center", fontsize=8)
    ax2.axvline(1.0, color="#b00", lw=1)
    ax2.set_yticks(y)
    ax2.set_yticklabels([l_ for _, l_ in labs], fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 1.6)
    ax2.set_title("Crown top bar wall under the B-25 sleeve\n(basis A, envelope 323 N static)", fontsize=10, loc="left")
    ax2.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2)
    fig.suptitle("BL-045  Crown: the B-25 mitre is off the bar, the sleeve still bears 38 mm; the real clamp and "
                 "housing leave B-25 clear", fontsize=12, x=0.01, ha="left")
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def fig_island(isl: dict, path: Path) -> str:
    """Section z 226 and z 218 around the right inboard boss: before (branch tip loose) and after (fused)."""
    import trimesh
    plt = _plt()
    from matplotlib.path import Path as MP
    fig, axs = plt.subplots(2, 2, figsize=(10, 8.6), dpi=100)
    files = {"before": OUT / "h1_assembled_before_bl045.stl",
             "after": REPO / "designs/pack_5200/print/frame_h1/h1_assembled.stl"}
    for j, (tag, f) in enumerate(files.items()):
        m = trimesh.load(f)
        for i, z in enumerate((226.0, 218.0)):
            ax = axs[i, j]
            s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            xs, ys = np.meshgrid(np.arange(70, 112, 0.25), np.arange(-16, 16, 0.25))
            P = np.c_[xs.ravel(), ys.ravel()]
            cnt = np.zeros(len(P), int)
            for e in s.discrete:
                cnt += MP(e[:, :2]).contains_points(P)
            G = (cnt % 2 == 1).reshape(xs.shape)
            ax.imshow(G, origin="lower", extent=(70, 112, -16, 16), cmap="Greys", vmin=0, vmax=1.6)
            ax.set_title(f"{tag}: section z {z:.0f}", fontsize=10)
            if i == 1:
                ax.set_xlabel("x (mm)")
            ax.set_ylabel("y (mm)")
            ax.add_patch(plt.Circle((96.0, 0.6), 8.0, fill=False, ec="#2b6cb0", lw=1.2, ls="--"))
            ax.text(97, 9.5, "boss r 8 (exact)", fontsize=8, color="#2b6cb0")
    b = isl["before"]["islands"][0] if isl["before"]["islands"] else None
    fig.suptitle("BL-045  Loose island in the lower half: the right lower-branch tip (x 80-89, z 217-234)\n"
                 + (f"before: {b['mm3']:.0f} mm3 dropped at ({b['centre'][0]:.0f}, {b['centre'][1]:.1f}, "
                    f"{b['centre'][2]:.0f}); " if b else "")
                 + f"after: {len(isl['after']['islands'])} islands, the tip is fused to the inboard boss as in the FEA",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def fig_imus(st: dict, path: Path) -> str:
    """IM / US fairlead strength before / after (rev C 1/FI99, fatigue) and the gap under the pin."""
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.2), dpi=100)
    names = list(st)
    y = np.arange(len(names))
    for ax, key, lab in ((axs[0], "sf", "rev C strength 1/FI99"), (axs[1], "fatigue", "rev C fatigue (1.6 g)")):
        a = [st[n]["bl042"][key] for n in names]
        b = [st[n]["bl045"][key] for n in names]
        ax.barh(y + 0.2, a, 0.38, color="#9aa1aa", label="BL-042 print (gap 1.9, throat 18)")
        ax.barh(y - 0.2, b, 0.38, color="#2f7d4f", label="BL-045 eye fairlead (gap 5.5, throat 20, saddle)")
        for i in range(len(names)):
            ax.text(a[i] + 0.05, y[i] + 0.2, f"{a[i]:.2f}", va="center", fontsize=8)
            ax.text(b[i] + 0.05, y[i] - 0.2, f"{b[i]:.2f}", va="center", fontsize=8)
        ax.axvline(1.0, color="#b00", lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{n.upper()} z {st[n]['z']:.0f}\n{st[n]['bl045']['force_n']:.0f} N" for n in names],
                           fontsize=8.5)
        ax.invert_yaxis()
        ax.set_title(lab, fontsize=10, loc="left")
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=1)
    fig.suptitle("BL-045  IM / US fairleads: every pin carries a webbing eye, so all ten get the hinge's clearance; "
                 "all pass; US gains most, IM1 / IM2 give some back", fontsize=11.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def _shrink(path: str, limit: int = 1_500_000) -> str:
    p = Path(path)
    if p.stat().st_size > limit:
        from PIL import Image
        im = Image.open(p)
        im = im.convert("P", palette=Image.ADAPTIVE, colors=128)
        im.save(p, optimize=True)
    return path


# ===================================================================================== compute + record
def compute(log=print) -> dict:
    from . import bag_attach as BA
    from . import crown_spine_clamp as CSC
    from . import crown_tube_guy_loop as CT
    from . import h1_fairleads as HF
    crown = CT.b25_topology_recheck()
    clamp = CSC.size_clamp()
    geo = CSC.h1_crown_interfaces()
    axis = CSC.spine_axis()
    b25 = CSC.b25_clearances(clamp, geo)
    strength = imus_strength(log=log)
    chk = HF.check_stl(HF.PRINT_DIR / "h1_assembled.stl")
    isl = island(log=log)
    revc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]
    pinfo = json.loads((REPO / "outputs" / "h1_buckling" / "print_info.json").read_text())
    hfl = json.loads((ANALYSIS / "h1_fairleads.json").read_text()) if (ANALYSIS / "h1_fairleads.json").exists() else {}
    res = {"date": "2026-11-13", "ticket": "BL-045",
           "crown_tube": crown, "clamp": clamp, "h1_crown_interfaces": geo, "spine_axis": axis, "b25": b25,
           "clamp_assumptions": CSC.ASSUMPTIONS,
           "pin_wrap": BA.PIN_WRAP, "envelopes": {s: BA.imus_eye_envelope(s) for s in BA.IMUS_STATIONS},
           "imus_strength": strength,
           "check_stl": {k: ({kk: v[kk] for kk in ("pass", "gap_under_pin", "throat_min_w", "eye_fits")
                              if kk in v} if isinstance(v, dict) else v) for k, v in chk.items()},
           "island": isl, "print_info": {k: pinfo[k] for k in ("assembled", "lower", "upper")},
           "fairleads_net_g": round(pinfo["fairleads_bl042"]["net_g"], 1),
           "h1_fairleads_mass": hfl.get("mass"), "h1_fairleads_body": hfl.get("body"),
           "revc_attach": {k: {"sf": revc["fairlead_fea"][k]["sf"], "fatigue": revc["fairlead_fea"][k]["sf_fatigue"],
                               "creep": revc["fairlead_fea"][k]["sf_creep"]} for k in ("hinge", "im3")},
           "revc_attach_previous": revc.get("bl045_previous_sf")}
    RESULTS.write_text(json.dumps(res, indent=1, default=_np))
    return res


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def figures(res: dict) -> list:
    from . import h1_fairleads as HF
    import trimesh
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [fig_crown(res["crown_tube"], res["clamp"], res["h1_crown_interfaces"], res["b25"], SCREENS / f"{SHOT}1.png"),
             fig_imus(res["imus_strength"], SCREENS / f"{SHOT}2.png"),
             HF.plot_slices(trimesh.load(HF.PRINT_DIR / "h1_assembled.stl"), SCREENS / f"{SHOT}3.png",
                            "BL-045 print: IM / US fairleads with the hinge's eye clearance (STL slices, right side)"),
             fig_island(res["island"], SCREENS / f"{SHOT}4.png")]
    return [_shrink(s) for s in shots]


def main(argv=None):
    res = compute()
    shots = figures(res)
    write_md(res, shots)
    print("SCREENSHOTS:\n" + "\n".join(shots))



# ===================================================================================== Markdown record
def _in(mm):
    return f"{mm / 25.4:.2f} in"


def _oz(g):
    return f"{g / 28.3495:.2f} oz"


def write_md(res: dict, shots: list) -> str:
    from . import crown_spine_clamp as CSC
    c, cl, g, ax, b = res["crown_tube"], res["clamp"], res["h1_crown_interfaces"], res["spine_axis"], res["b25"]
    st, isl = res["imus_strength"], res["island"]
    ck = c["checks"]
    L = []
    a = L.append
    a("# Crown tube with the B-25 mitre, spine clamp, IM / US fairleads, loose island (BL-045)\n")
    a("structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-045-crown-and-fairlead-checks.md`. Code: "
      "`huntkit/gendesign/bl045_checks.py` (`python -m huntkit.gendesign.bl045_checks`) collecting "
      "`crown_tube_guy_loop.b25_topology_recheck`, `crown_spine_clamp.py` (new), `bag_attach.eye_geom / "
      "imus_eye_envelope` (new), `h1_fairleads`, `frame_h1.print_mesh`. Tests: `tests/test_bl045_crown_fairleads.py`. "
      "Results: `crown_and_fairlead_checks.json`. Checked on the real geometry: the H1 print STL (sliced), the frame "
      "beam model (rev C sets on the three crown kits), `corrie_f.b25_topology` and SK-12.\n")
    # ---------------- summary
    a("## Result in short\n")
    a(f"1. **Crown tube: BL-041's 1.36 / 1.27 is confirmed** (re-run: {ck['vector']['sf_static']:.2f} static, "
      f"{ck['vector']['sf_fatigue']:.2f} fatigue on the real pull vectors). The 45 deg mitre, the drop and the necked "
      f"run all sit 14 mm or more below the bar's underside, so only the 38 mm sleeve bears on the bar. The run's "
      f"tension (the guy's outboard part, up to {c['max_outboard_share']:.0%}) pulls the sleeve down through the drop; "
      f"with the real directions the radial load is {c['k_vector_max']:.3f} x BL-041's scalar sum. Taking that run "
      f"pull in line with the guy (a bound) gives {ck['bound']['sf_static']:.2f} / {ck['bound']['sf_fatigue']:.2f}. "
      f"TL-1's proof moves 494 -> **{c['proof_tl1_n']:.0f} N**.")
    a(f"2. **Spine clamp: real dimensions published** (`crown_spine_clamp`). The joint carries "
      f"{cl['loads_max_factored']['spine_M_max_nm']:.0f} N m and {cl['loads_max_factored']['spine_N_max_n']:.0f} N "
      f"factored (never checked before). Sized as the frame's own bonded joint: 7075 T-fitting, saddle "
      f"**{cl['saddle_len_mm']:.0f} mm along the bar (half-width {cl['half_x_mm']:.1f}, was 15 assumed)**, socket "
      f"{cl['socket_len_mm']:.0f} mm, **collar {cl['collar_below_bar_underside_mm']:.1f} mm below the bar (was 12 "
      f"assumed)**, {cl['mass_g']:.1f} g (frame.yaml books 6.0). Real pawl housing from the STL: **{g['pawl_housing_up_mm']:.1f} "
      f"mm above the pawl line (was 20), |x| {g['pawl_housing_half_w_mm']:.1f} (was 18)**. **B-25's clearances hold**: "
      f"band to clamp {b['band_to_clamp_x_mm']:.1f} mm (>= 10), spine wrap {b['kits']['S']['wrap_to_housing_mm']:.1f} mm "
      f"above the housing at kit S 15 in (BL-043: 13), mitre {b['kits']['S']['mitre_to_body_in_band_mm']:.1f} mm above "
      f"the printed body. **But the spine sits {ax['spine_axis_minus_bar_axis_y_mm'] * -1:.1f} mm fore of the bar** "
      f"(the printed channel), so B-25's run is {CSC.B25_RUN_EXTRA_PER_SIDE_MM:.0f} mm longer a side (cut "
      f"+{CSC.B25_CUT_CHANGE_MM:.0f} mm), and **the OD 20 spine tube does not fit the printed channel** "
      f"({ax['channel_depth_y_mm']:.1f} mm deep; see Found, not fixed).")
    a("3. **IM / US fairleads: webbing wraps all ten pins** (IME 38 mm eyes at IM1-IM3, the US 25 mm eye and the cam "
      "anchor at US1-US2; hooks and carabiners clip the eyes, never a pin). A necked 38 mm eye is 3 plies (4.5 mm) "
      "and could not pass the 1.9 mm gap. **All ten now carry the hinge's clearance** (gap 5.5, throat 20, saddle; "
      "on the crown sleeve the root stops 1 mm above the bore), in the print files, slice-checked "
      f"**{sum(1 for k, v in res['check_stl'].items() if isinstance(v, dict) and v['pass'])} / 12 with the eye stack**. "
      "Every station passes. The US fairleads gain most: their fatigue was below 1.0 at the cradle load before "
      f"({st['us2']['bl042']['fatigue']:.2f}) and is {st['us2']['bl045']['fatigue']:.2f} now (saddle on a solid stay). "
      "IM1 / IM2 lose margin (the pin rises 3.6 mm and the bore limits the root): IM2 fatigue "
      f"{st['im2']['bl042']['fatigue']:.2f} -> {st['im2']['bl045']['fatigue']:.2f}; IM3 on the sim loads "
      f"{st['im3']['bl042']['sim_worst']['fatigue']:.2f} -> {st['im3']['bl045']['sim_worst']['fatigue']:.2f} (goal 1.15).")
    ib = isl["before"]["islands"][0] if isl["before"]["islands"] else None
    a(f"4. **Loose island: found and fixed.** " + (f"The {ib['mm3']:.0f} mm3 piece at ({ib['centre'][0]:.0f}, "
      f"{ib['centre'][1]:.1f}, {ib['centre'][2]:.0f}) " if ib else "") + "is the tip of the right lower branch. The 2 mm "
      "voxel body (and so every FEA) joins it to the inboard bolt boss below z 234; the print export took the whole "
      "voxel boss out of the smoothing field before adding the exact boss, which opened a one-voxel gap. The field "
      "now keeps the boss voxels up to 2 mm inside the capsule (`frame_h1.BOSS_CORE_MM`): no half drops anything.")
    a(f"5. **Stale records re-run:** rev C hinge cheek 2.97 -> **{res['revc_attach']['hinge']['sf']:.2f}** (fatigue "
      f"{res['revc_attach']['hinge']['fatigue']:.2f}) on the BL-042 geometry; IM3 "
      f"{(res.get('revc_attach_previous') or {}).get('im3', float('nan')):.2f} -> {res['revc_attach']['im3']['sf']:.2f}; "
      "'fairleads present 1.000' removed from `h1_buckling.md` (now the voxel stub fraction + the STL slice check) and "
      "from `frame_fixed.py`.\n")
    pi = res["print_info"]
    a(f"**Mass:** printed body {pi['assembled']['g']:.1f} g ({_oz(pi['assembled']['g'])}; was 845.7): fairleads "
      f"{res['fairleads_net_g']:+.1f} g net (was +37.2; the ten new saddles +13.3 g), island fix +2.6 g. Spine clamp "
      f"{cl['mass_g']:.1f} g against 6.0 booked (+{cl['mass_g'] - 6.0:.1f} g, not in the ledger yet). B-25 cut "
      f"+{CSC.B25_CUT_CHANGE_MM:.0f} mm of 38 mm webbing (+{CSC.B25_CUT_CHANGE_MM * 28 / 1000:.2f} g).\n")
    # ---------------- 1
    a("## 1. Crown tube under B-25 as BL-043 built it\n")
    a("**What bears on the bar** (`corrie_f.b25_topology`, s = down the spine from the bar centre, bar radius 9):\n")
    a("| part | x mm | s mm | on the bar? |")
    a("|---|---|---|---|")
    t = c["topology"]
    a(f"| sleeve (1 wrap + 15 mm lap, 38 mm) | {t['band_x'][0]}-{t['band_x'][1]} | round the bar | **yes, 38 mm** |")
    for k, v in t["off_bar"].items():
        a(f"| {k} | {'band' if k != 'necked run + spine wrap' else '11.2-26.5, round the spine'} | {v['s_mm'][0]}-{v['s_mm'][1]} | "
          f"no ({v['below_bar_underside_mm']:.0f} mm below the underside) |")
    a("")
    a("The mitre's extra layers lie on the aft face of the drop, below the bar: they add no bearing and take none away. "
      f"The toggle tab is now the full {t['tab_width_mm']:.0f} mm strip (BL-041 had a 25 mm tab on a 38 mm sleeve); "
      f"the {t['toggle_len_mm']:.0f} mm POM toggle spreads into it.\n")
    a("**Pull direction.** Per sim run and side: the guy's direction at the bar (port routing), the crown strap's, "
      "and the run tension = guy x its outboard share (the drop pulls the sleeve straight down). Radial (y-z) "
      "resultant against BL-041's scalar sum (guy + strap):\n")
    a("| torso | case | side | guy 1 g N | strap 1 g N | guy below horizontal | outboard share | run tension N | radial N | / scalar |")
    a("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in c["runs"]:
        a(f"| {r['torso']:g} | {r['case']} | {r['side']} | {r['guy_1g_n']:.1f} | {r['crown_1g_n']:.1f} | "
          f"{r['guy_angle_below_horizontal_deg']:.0f} deg | {r['outboard_share']:+.3f} | {r['run_tension_1g_n']:.1f} | "
          f"{r['radial_1g_n']:.1f} | {r['k_vector']:.3f} |")
    a(f"\nAt 23 in the guy runs 57-59 deg below horizontal and the drop pulls down too, so they add; the crown strap pulls "
      f"up and aft and takes some back. Worst ratio **{c['k_vector_max']:.3f}** (23 in fill, left). With the run "
      f"tension put in line with the guy (bound) {c['k_bound_max']:.3f}. An inboard pull (up to "
      f"{c['max_inboard_share']:.0%} at 15 in) slackens the run; the sleeve is then held by its own grip, "
      f"{b['band_to_clamp_x_mm']:.1f} mm short of the clamp.\n")
    a("**Ring check (basis A, rev C bar, envelope 323 N static / 172 N fatigue peak x the ratio):**\n")
    a("| case | width mm | static N | capacity N (kd) | static SF | fatigue SF |")
    a("|---|---:|---:|---:|---:|---:|")
    for k, lab in (("bl041_scalar", "BL-041 scalar sum (record)"), ("vector", "real pull vectors"),
                   ("bound", "run tension in line (bound)"), ("vector_toggle_width", "vectors, 30 mm (toggle only)"),
                   ("bound_toggle_width", "bound, 30 mm (toggle only)")):
        r = ck[k]
        a(f"| {lab} | {r['width_mm']:.0f} | {r.get('static_n', ck['vector' if 'vector' in k else 'bound']['static_n']):.0f} | "
          f"{r['capacity_n']:.0f} | **{r['sf_static']:.2f}** | **{r['sf_fatigue']:.2f}** |")
    a(f"\n- **Confirmed: 1.36 / 1.27 stands** (1.35 / 1.27 on the vectors). The bound still passes (1.22 / 1.14).")
    a("- The only way it fails is if the 30 mm toggle's pull did not spread over the 38 mm sleeve AND the run pulled "
      "in line (0.97 / 0.91). ASSUMPTION WIDE_SLEEVE stays (spread 4 mm a side over the 30 mm tab leg, milder than "
      "BL-041's 6.5 mm from a 25 mm tab); TL-1 tests the as-built part and settles it.")
    sw = c["spine_wrap"]
    a(f"- Spine wall under the 25 mm spine wrap: run tension {sw['run_tension_factored_n']:.0f} N factored, basis A "
      f"capacity {sw['capacity_n']:.0f} N: SF {sw['sf']:.1f}.")
    a(f"- **TL-1 proof {c['proof_tl1_n']:.0f} N** (323 x {c['k_vector_max']:.3f} / 0.654; 494 before). The rig pulls "
      "the guy toggle 57 deg below horizontal and 14 % outboard (the worst measured), with the run's spine end "
      "anchored: then the drop leg loads the sleeve as on the frame.\n")
    # ---------------- 2
    a("## 2. Spine clamp: real dimensions\n")
    lm = cl["loads_max_factored"]
    a("**Loads** at the spine-to-bar node TB1 of the frame model (`huntkit.fea.pack5200`, built by `crown_diet.build` "
      "for kits S / M / L at both ends of their range, every HA-LS-1 rev C set, both couple variants; factored):\n")
    a(f"- spine end: N {lm['spine_N_max_n']:.0f} N, V {lm['spine_V_max_n']:.0f} N, M **{lm['spine_M_max_nm']:.1f} N m** "
      f"({lm['spine_M_set']});")
    a(f"- jump in the bar across TB1: torsion {lm['bar_T_jump_max_nm']:.1f} N m, bending {lm['bar_M_jump_max_nm']:.1f} N m.\n")
    a("A 6 g split collar that only grips has no rated slip under 55 N m, so the clamp is sized as the frame's own "
      "joint (ASSUMPTION CLAMP-TYPE): a machined 7075-T6 T-fitting bonded with MMA at the crown corners' 0.8 mm "
      "bondline, checked by `huntkit.fea.joints.bond_check` with HA-LS-1 rev C's bond rule (average >= case factor, "
      "Volkersen peak >= 1.0 at limit, fatigue <= 0.3 x lap shear at 1.6 g):\n")
    a("| bond | length mm | average | peak (limit) | fatigue avg | fatigue peak | with transverse shear (avg / peak) |")
    a("|---|---:|---:|---:|---:|---:|---|")
    for k, lab, Lk in (("socket", "socket on the spine", "socket_len_mm"), ("saddle", "saddle on the bar", "saddle_len_mm")):
        m, ms = cl["margins"][k], cl["margins"][k + "_with_shear"]
        a(f"| {lab} | {cl[Lk]:.0f} | {m['avg']['sf']:.2f} | {m['peak']['sf']:.2f} | {m['fat_avg']['sf']:.2f} | "
          f"{m['fat_peak']['sf']:.2f} | {ms['avg']['sf']:.2f} / {ms['peak']['sf']:.2f} |")
    sb = cl["margins"]["socket_bending"]
    a(f"\nThe bond rule alone asks {cl['socket_len_bond_min_mm']:.0f} mm of socket and {cl['saddle_len_bond_min_mm']:.0f} mm "
      f"of saddle; the socket is set to 15 mm (ASSUMPTION SOCKET-MIN) and the saddle to the socket's OD (24 mm). The "
      f"wall is 0.8 mm: a 1.5 mm saddle is stiffer and its Volkersen peak on the bar never reaches 1.0 (0.93 plateau). "
      f"Socket bending: {sb['sigma_factored_mpa']:.0f} MPa factored, yield SF {sb['sf_yield']:.2f}; fatigue (Kt 2) "
      f"{sb['sf_fatigue_kt2']:.2f}. With the transverse shear added to the bond (the joints module sends it to bearing "
      f"at the lip), the saddle's peak is 0.78: the T6 coupon of the fitting must cover it.\n")
    a("**Geometry measured on the H1 print STL** (`h1_crown_interfaces`):\n")
    a("| item | BL-043 assumed | real | source |")
    a("|---|---:|---:|---|")
    a(f"| pawl housing top above the pawl line | 20 | **{g['pawl_housing_up_mm']:.1f}** (z {g['pawl_housing_top_z']:.1f}) | STL vertices |")
    a(f"| pawl housing half-width | 18 | **{g['pawl_housing_half_w_mm']:.1f}** | STL sections z 520.5-536 |")
    a(f"| body top in the B-25 band (|x| 26.5-64.5) | 531 (OD 22 upper bar) | **{g['body_top_z_in_b25_band']:.1f}** | STL vertices |")
    a(f"| spine channel (x by y) | - | {g['spine_channel_width_x_mm']:.1f} x **{g['spine_channel_depth_y_mm']:.1f}** mm, centre y "
      f"{g['spine_channel_centre'][1]:.1f} | STL sections z 510-530 |")
    a(f"| spine axis to bar axis (fore) | 0 (coplanar) | **{-ax['spine_axis_minus_bar_axis_y_mm']:.2f}** | channel centre vs frame model |")
    a(f"| clamp half-width along the bar | 15 | **{cl['half_x_mm']:.1f}** | size_clamp |")
    a(f"| clamp collar below the bar | 12 | **{cl['collar_below_bar_underside_mm']:.1f}** | size_clamp (socket from s {cl['s_full_circumference_mm']:.1f} for 15 mm) |")
    a(f"| clamp fore / aft faces from the bar axis | - | {cl['fore_face_from_bar_axis_mm']:.1f} fore / {cl['aft_face_from_bar_axis_mm']:.1f} aft | size_clamp |")
    a(f"| clamp mass | 6.0 | **{cl['mass_g']:.1f} g** | 7075 + MMA volumes |")
    a("")
    a("**B-25 on the real clamp and housing** (corrie_f.b25_topology's checks, each crown kit at its shortest torso):\n")
    a("| kit | torso in | spine wrap to housing mm | run to body mm | mitre to body in band mm | mitre to housing side (x) mm | ok |")
    a("|---|---:|---:|---:|---:|---:|---|")
    for k, v in b["kits"].items():
        a(f"| {k} | {v['torso_in']:g} | {v['wrap_to_housing_mm']:.1f} | {v['run_to_body_mm']:.1f} | "
          f"{v['mitre_to_body_in_band_mm']:.1f} | {v['mitre_to_housing_side_x_mm']:.2f} | {'yes' if v['ok'] else '**no**'} |")
    a(f"\nBand to clamp: **{b['band_to_clamp_x_mm']:.1f} mm** (>= 10). The run top moves to s {b['run_top_s_mm']:.1f} "
      f"(BL-043: 23.0). The mitre ends {b['kits']['S']['mitre_to_housing_side_x_mm']:.1f} mm outboard of the housing's "
      "side; in height it is 3.6 mm above the housing top and it lies on the bar's aft face, about 13 mm aft of the "
      "housing, so the real 3D gap is larger than either number.\n")
    rp = b["run_plan_mm"]
    a(f"**The run is longer than drawn.** SK-12 draws the spine in the bar's plane. The printed channel puts the spine "
      f"axis {rp['spine_axis_fore_of_bar_mm']:.2f} mm fore of the bar, so the run from the mitre (on the bar's aft "
      f"face) to its tangent on the spine wrap is {rp['run_real_mm']:.1f} mm in plan, not {rp['run_bl043_mm']:.1f}: "
      f"**B-25 cut +{rp['cut_change_mm']:.0f} mm** (`crown_spine_clamp.B25_CUT_CHANGE_MM`). The run then crosses "
      "below the clamp collar toward the wearer side to reach the spine; nothing of it is above the bar.\n")
    a("**Constants for the pack-designer** (import from `huntkit.gendesign.crown_spine_clamp`; corrie_f is not edited "
      "here):\n")
    a("```")
    for k in ("SPINE_CLAMP_HALF_X", "SPINE_CLAMP_COLLAR", "SPINE_AXIS_FORE_MM", "SPINE_CLAMP_MASS_G", "PAWL_HOUSING_UP",
              "PAWL_HOUSING_HALF_W", "BODY_TOP_Z_IN_B25_BAND", "B25_RUN_EXTRA_PER_SIDE_MM", "B25_CUT_CHANGE_MM"):
        a(f"{k} = {getattr(CSC, k)}")
    a("```")
    a("They replace corrie_f's SPINE_CLAMP_HALF (15), SPINE_CLAMP_COLLAR (12), PAWL_HOUSING_UP (20), "
      "PAWL_HOUSING_HALF_W (18) and the OD 22 upper-bar top. With them, `b25_topology`'s `clamp_envelope` (half_x <= "
      "16.5, collar <= 25) holds.\n")
    # ---------------- 3
    a("## 3. IM / US fairleads: what passes round each pin\n")
    a("| station | wraps the pin | clips the eye (not the pin) |")
    a("|---|---|---|")
    for k, v in res["pin_wrap"].items():
        a(f"| {k.upper()} | {v['wraps']} | {v['clips_on_the_eye']} |")
    a("\nSources: `patterns_corrie_f_rev3` pieces IME (6 x 200 mm, 38 mm) and US (2 x 550 mm, 25 mm, 50 mm eye fold "
      "'round the left pin sleeve'); `mfg_corrie_f_rev3` load points ('IM fairlead eyes (6) ... captive in the printed "
      "fairleads', 'US1/US2 sewn eye on the left pin', BOM 'US-anchor'), SK-11, `attach_system` ('captive eyes sit on "
      "pins in UHMWPE sleeves in an 18 mm throat'). Every pin carries webbing, so every one gets an envelope like the "
      "hinge's.\n")
    e = res["envelopes"]["im1"]
    a("**Envelope** (`bag_attach.imus_eye_envelope(station)`, same keys as `HINGE_EYE_ENVELOPE`): neck 18 mm (the 38 mm "
      "IME with each edge folded 10 mm in, as the HE; the 25 mm US eye and cam anchor with each edge folded 3.5 mm in), "
      f"gap under the pin **{e['gap_under_pin_mm']:.1f} mm** (3 plies x 1.5 + 1.0; the 2-ply US eye has 2.5 mm spare), "
      f"throat **{e['throat_mm']:.0f} mm** (19 mm widest neck + 1). One geometry for all ten (`bag_attach.eye_geom`): "
      "the hinge's section with a saddle on the station's own stay; on the crown sleeve (IM1-IM3) the root stops 1 mm "
      "above the 18 mm reamed bore (ASSUMPTION EYE-ROOT), so the bore stays open (checked on the STL at z 190 / 330 / "
      "520).\n")
    a("**Strength** (`h1_fairleads.fairlead_fea`, 1 mm voxels, crown bore empty at IM1-IM3; rev C governing factored "
      "vectors from `rev_c_verification`; US = the 720 N cradle load of loadpath S5-S7, aft and down at the cradle "
      "angle):\n")
    a("| station | load N (case) | BL-042 print: 1/FI99 / fatigue / creep | **BL-045: 1/FI99 / fatigue / creep** | pin yield / fatigue (BL-045) | sim worst (BL-045) |")
    a("|---|---|---|---|---|---|")
    for k, v in st.items():
        o, n = v["bl042"], v["bl045"]
        sim = n.get("sim_worst")
        a(f"| {k.upper()} z {v['z']:.0f} | {n['force_n']:.0f} ({v['load']['case']}) | {o['sf']:.2f} / {o['fatigue']:.2f} / "
          f"{o['creep']:.2f} | **{n['sf']:.2f} / {n['fatigue']:.2f} / {n['creep']:.2f}** | {n['pin']['sf_yield']:.2f} / "
          f"{n['pin']['sf_fatigue']:.2f} | " + (f"strength {sim['strength']:.2f}, fatigue {sim['fatigue']:.2f} "
                                                f"({sim['run']}; BL-042 {o['sim_worst']['fatigue']:.2f})" if sim else "-") + " |")
    a("\nRequirements: 1/FI99 >= 1.0 on the factored load, fatigue >= 1.0 (rev C), >= 1.15 on the sim loads (BL-021 "
      "goal), creep >= 1.0. The longer pin span (throat 20) costs the pin a little; it stays above 1.\n")
    ch = res["check_stl"]
    a("**Print files re-exported** (`h1_buckling.export_print`) and slice-checked with each station's eye stack "
      "(`h1_fairleads.check_stl`, the eye polygon shrunk by the 0.05 mm simplify tolerance, `EYE_MESH_TOL`):\n")
    a("| station | gap under pin mm | throat mm | eye stack clear | pass |")
    a("|---|---:|---:|---|---|")
    for k, v in ch.items():
        if isinstance(v, dict):
            a(f"| {k} | {v['gap_under_pin']:.2f} | {v['throat_min_w']:.1f} | {v.get('eye_fits')} | {'yes' if v['pass'] else '**no**'} |")
    hb = res.get("h1_fairleads_body") or {}
    if hb.get("bases"):
        a("\nBody checks on the voxel body as printed (throats cleared, holes emptied, all twelve saddles added inside "
          "the envelope; `h1_fairleads.body_recheck`):\n")
        a("| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after |")
        a("|---|---|---|---|---|")
        for bb, v in hb["bases"].items():
            a(f"| {bb} | {v['before']['strength']:.3f} / {v['after']['strength']:.3f} | {v['before']['fatigue']:.3f} / "
              f"{v['after']['fatigue']:.3f} | {v['before']['creep']:.3f} / {v['after']['creep']:.3f} | "
              f"{v['before']['buckling']:.3f} / {v['after']['buckling']:.3f} |")
    a("\n**The bag side must change** (pack-designer, BL-044's files): the IME eyes (op 'IME fairlead eyes') and the US "
      "eyes need the 18 mm neck where they pass the throat, as op 4.05 does for the HE; the US cam needs a drawn anchor "
      "(a necked 25 mm loop round the right pin, box-X to the cam bar, as IMC does for the IM cams). HE-FIT's dry fit "
      "should be repeated on one IM and one US fairlead.\n")
    # ---------------- 4
    a("## 4. Lower-half export: the loose island\n")
    a("| | before (git 5c54df9) | after |")
    a("|---|---|---|")
    a(f"| lower-half shells after the z 234 split | {isl['before']['lower_shells']} | {isl['after']['lower_shells']} |")
    a(f"| dropped piece | " + (f"{ib['mm3']:.0f} mm3 at ({ib['centre'][0]:.1f}, {ib['centre'][1]:.1f}, {ib['centre'][2]:.1f}), "
      f"bounds {ib['bounds']}" if ib else "none") + " | none |")
    a(f"| printed body g | {isl['before']['assembled_g']:.1f} | {isl['after']['assembled_g']:.1f} |\n")
    a("**What it was.** The tip of the right lower inboard branch, x 80-89, z 217-234. In the 2 mm voxel body the "
      "lower half (z < 234) is one 6-connected piece: the tip is joined to the inboard bolt boss (axis x 96) over z "
      "217-233. `frame_h1.print_mesh` removed every boss voxel from the smoothing field and then added the exact r 8 "
      "capsule; the 0.7-voxel Gaussian and the 0.5 level pulled the branch surface back about one voxel from the "
      "capsule, so in the mesh the tip touched nothing below z 234 and the split dropped it (it carried load in the "
      "FEA: the joint check takes the cut through stay + bosses + branch). The left side happened to stay fused.\n")
    a("**Fix.** Only the boss core (deeper than `BOSS_CORE_MM` = 2 mm inside the capsule) leaves the field, so the smooth "
      "body overlaps the exact capsule and fuses where the voxels do. Side effects measured: +2.6 g (thin skins round "
      "the four bosses), the outboard boss stands up to 1.2 mm proud of its capsule on the left (|x| 140.6, inside the "
      "152 limit), the wearer and bag faces unchanged, the nut pockets keep their hex (they are cut after). "
      "`h1_buckling.md` now says so instead of 'carries nothing'.\n")
    # ---------------- 5
    a("## 5. Stale records\n")
    pv = res.get("revc_attach_previous") or {}
    a(f"- `rev_c_verification` attachments re-run on the printed geometry (`refresh_attachments`; the cheek FE is "
      f"`h1_fairleads.fairlead_fea` with the crown bore empty at IM3): hinge {pv.get('hinge', float('nan')):.2f} -> "
      f"**{res['revc_attach']['hinge']['sf']:.2f}** (fatigue {res['revc_attach']['hinge']['fatigue']:.2f}, creep "
      f"{res['revc_attach']['hinge']['creep']:.2f}), IM3 {pv.get('im3', float('nan')):.2f} -> "
      f"**{res['revc_attach']['im3']['sf']:.2f}**. Nothing else in that record depends on the fairlead geometry.")
    a("- `h1_buckling.md` keep-outs: 'fairleads present 1.000' is gone; the record prints the voxel stub fraction under "
      "its real name and the STL slice check. The generator now also prints BL-039's corrected spreader-share text "
      "(a re-run had been restoring BL-037's wrong sentence).")
    a("- `frame_fixed.py` (fixed-torso study) labels the same number 'fairlead stubs inside the envelope present "
      "(voxel)'. Its stored `frame_fixed_results.json` (not re-run: a study, not adopted) and `frame_h1_results.json` "
      "keep the old key.\n")
    # ---------------- assumptions
    a("## Assumptions that govern\n")
    for k, v in res["clamp_assumptions"].items():
        a(f"- ASSUMPTION {k}: {v[0]} Settled by: {v[1]}")
    a("- ASSUMPTION GUY-DIR: rev 3's guy direction at the bar = the rev 2 port runs' (same B-27 -> B-22 routing). "
      "Settled by: PORT-1 / T9 guy angle at each kit.")
    a("- ASSUMPTION RUN-TENSION: the run carries the guy's outboard part with no sleeve friction. Settled by: TL-1 pulled "
      "at the worst measured angle.")
    a("- ASSUMPTION WIDE_SLEEVE (kept): the 30 mm toggle's pull spreads over the 38 mm sleeve. Settled by: TL-1.")
    a("- ASSUMPTION EYE-ROOT: on IM1-IM3 the saddle root stops 1 mm above the reamed bore. Settled by: IM3-EC coupon "
      "(re-cut from the new file) and first-article bore ream.")
    a("- ASSUMPTION HE-T / HE-GAP-MARGIN / HE-NECK-TOL (BL-042) now also govern the IM / US eyes. Settled by: HE-FIT "
      "repeated on one IM and one US fairlead.\n")
    a("## Found, not fixed\n")
    a(f"- **The OD 20 spine tube does not fit the printed spine channel** ({g['spine_channel_width_x_mm']:.1f} x "
      f"{g['spine_channel_depth_y_mm']:.1f} mm through the pawl housing, z 510-530). The channel was sized for the old "
      "30 x 3 mm plate spine; the tube plus the 6 mm rack needs at least 26 mm one way. A frame change (channel and "
      "housing) or a spine change; it also fixes where the spine axis really is (here: the channel centre).")
    a("- The frame model (`pack5200`) puts the spine in the bar plane; the print puts it 15.85 mm fore. The 15.85 mm "
      "offset adds about 750 N x 15.85 mm = 12 N m to the clamp in the worst set; the model does not carry it.")
    a("- The spine clamp (10.4 g) and the B-25 cut (+34 mm) are not in the ledger; frame.yaml still books 6 g.")
    a("- The US cam on the right pin has no drawn anchor part (BOM 'US-anchor' only).")
    a("- `frame_fixed_results.json` and `frame_h1_results.json` keep the old 'fairleads present' key (not re-run).")
    a("- Ledger H1F now reads 50.4 g from `h1_fairleads.json`; the print mesh (861.6 g) is still 10 g above raster + "
      "H1F (smoothing).\n")
    a("## Screenshots\n")
    for s in shots:
        a(f"- `{Path(s).relative_to(REPO)}`")
    DOC.write_text("\n".join(L) + "\n")
    return str(DOC)


if __name__ == "__main__":
    main()
