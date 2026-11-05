"""Results summary (JSON), plots (PNG), GLB + offline viewer for the pack cloth sim."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .fabric import seam_strength_n_mm
from .model import Membrane
from .results import capped_volume, chain_order, seam_forces, tri_measures, volume_centroid

SPREADER = {"x_half": 121.0, "z": (112.0, 430.0)}     # spreader_results.json chosen: 242 x 318, z 112-430
WRINKLE_STRAIN = -0.02                                # min principal strain below which the cloth is slack (wrinkles)


def _f(v, nd=3):
    return float(round(float(v), nd))


def group_seams(sf: dict) -> dict:
    """Merge seam fragments by piece pair (and by edge pair for seams inside one piece)."""
    out = {}
    for nm, s in sf.items():
        a, b = s["pieces"]
        key = f"{a} | {b}" if a != b else f"{a} {s['edges'][0]}|{s['edges'][1]}"
        if a == b and ("dart" in s["edges"][0]):
            key = f"{a} {s['edges'][0].split('_')[0]}"
        g = out.setdefault(key, {"pieces": (a, b), "parts": [], "line": [], "trib": [], "flags": [], "nodes": []})
        g["parts"].append(nm)
        g["line"].append(s["line_n_mm"])
        g["trib"].append(s["trib_mm"])
        g["flags"] += s["flags"]
        g["nodes"].append(s["nodes"])
    for k, g in out.items():
        line, trib = np.concatenate(g.pop("line")), np.concatenate(g.pop("trib"))
        nodes = np.concatenate(g.pop("nodes"))
        ok = np.array([f == "" for f in g["flags"]])
        use = line[ok] if ok.any() else line
        g.update(max_n_mm=float(use.max()), p95_n_mm=float(np.percentile(use, 95)),
                 mean_n_mm=float(np.average(use, weights=trib[ok] if ok.any() else trib)),
                 length_mm=float(trib.sum()), max_flagged_n_mm=float(line.max()),
                 max_node=int(nodes[ok][np.argmax(use)] if ok.any() else nodes[np.argmax(line)]))
        g.pop("flags")
    return out


def summarize(pm, case_name: str, case: dict, x: np.ndarray, sim, infos) -> dict:
    m = pm.mesh
    memb = Membrane(m)
    tm = tri_measures(m, memb, x)
    pres = sim.term("gas")
    V = pres.volume(x)
    # body volume: everything below the collar seam, capped there
    collar = [k for k in pm.seams if not k.startswith("_") and "B-06.bottom" in k]
    segs = [sgm for k in collar for sgm in pm.seams[k]["segments"]]
    loop = chain_order(segs)
    body_t = m.tris[m.tri_piece != m.piece_index("B-06")]
    Vb = capped_volume(x, body_t, loop)
    Vb0 = capped_volume(m.X0, body_t, loop)
    cg = volume_centroid(x, m.tris)
    out = {"case": case_name, "inputs": case,
           "solve": [{"stage": i.reason, "iterations": i.iterations, "residual_n": _f(i.residual_n, 4),
                      "seconds": _f(i.seconds, 1), "converged": bool(i.converged)} for i in infos],
           "converged": bool(infos[-1].converged), "mesh": {"nodes": m.n, "triangles": len(m.tris), "h_mm": pm.h}}
    out["volume"] = {"closed_L": _f(V / 1e6), "closed_cu_in": _f(V / 16387.064, 0),
                     "body_below_collar_seam_L": _f(Vb / 1e6), "body_as_drafted_L": _f(Vb0 / 1e6),
                     "collar_to_fill_line_L": _f((V - Vb) / 1e6),
                     "design_L": _f(pm.c["design_volume_L"]), "release_pattern_check_L": pm.c["pattern_volume_L_release"],
                     "contents_cg_mm": [_f(c, 1) for c in cg]}
    out["fill"] = dict(getattr(pm, "fill_info", {}))
    if case.get("meat_kg"):
        out["meat"] = dict(getattr(pm, "meat_info", {}))
    out["area"] = {"flat_m2": _f(m.flat_area() / 1e6, 4), "sewn_m2": _f(tm["area"].sum() / 1e6, 4),
                   "ratio": _f(tm["area"].sum() / m.flat_area(), 4)}
    # strains per piece
    pieces = {}
    for pi, p in enumerate(m.pieces):
        s = m.tri_piece == pi
        a = tm["area"][s]
        em = tm["e_max"][s]
        order = np.argsort(em)
        cw = np.cumsum(a[order]) / a.sum()
        p99 = em[order][min(np.searchsorted(cw, 0.99), len(em) - 1)]
        wr = tm["e_min"][s] < WRINKLE_STRAIN
        pieces[p.name] = {"material": p.meta.get("material_id"), "label": p.meta.get("label"),
                          "mass_g": _f((m.A0[s].sum() * p.fabric.areal_kg_mm2) * 1e3, 1),
                          "e_max_pct": _f(em.max() * 100, 2), "e_p99_pct": _f(p99 * 100, 2),
                          "warp_max_pct": _f(tm["e_warp"][s].max() * 100, 2),
                          "weft_max_pct": _f(tm["e_weft"][s].max() * 100, 2),
                          "shear_max_deg": _f(np.degrees(np.abs(tm["shear_rad"][s]).max()), 1),
                          "t_max_n_mm": _f(tm["t_max"][s].max(), 3),
                          "wrinkle_area_pct": _f(a[wr].sum() / a.sum() * 100, 1)}
    out["pieces"] = pieces
    hot = np.argsort(tm["e_max"])[::-1]
    spots, seen = [], []
    for t in hot:
        c = tm["centroid"][t]
        if any(np.linalg.norm(c - s_) < 80 for s_ in seen):
            continue
        seen.append(c)
        spots.append({"piece": m.pieces[m.tri_piece[t]].name, "xyz_mm": [_f(v, 0) for v in c],
                      "e_max_pct": _f(tm["e_max"][t] * 100, 2), "t_max_n_mm": _f(tm["t_max"][t], 3)})
        if len(spots) >= 6:
            break
    out["hot_spots"] = spots
    # seams
    cab = sim.term("cables")
    att_nodes = [int(n) for c in cab.cables for n in c.nodes if n >= 0 and c.kind in ("hook", "roll_clip")]
    att_nodes += [int(n) for n in getattr(pm, "hinge_nodes", [])]
    sf = seam_forces(m, x, memb, pm.seams, exclude=att_nodes)
    gs = group_seams(sf)
    sc = pm.scen["seams"]
    mats = {p.name: p.meta.get("material_id") for p in m.pieces}
    seams = {}
    for k, g in gs.items():
        a, b = g["pieces"]
        st = seam_strength_n_mm(mats[a], mats[b], sc["thread"], float(sc["stitch_mm"]), str(sc["stitch"]))
        seams[k] = {"max_n_mm": _f(g["max_n_mm"], 3), "p95_n_mm": _f(g["p95_n_mm"], 3), "mean_n_mm": _f(g["mean_n_mm"], 3),
                    "length_mm": _f(g["length_mm"], 0), "max_at_mm": [_f(v, 0) for v in x[g["max_node"]]],
                    "max_incl_ends_attachments_n_mm": _f(g["max_flagged_n_mm"], 3),
                    "strength_n_mm": _f(st["strength_n_mm"], 1), "governs": st["governs"],
                    "sf": _f(st["strength_n_mm"] / max(g["max_n_mm"], 1e-9), 1)}
    out["seams"] = dict(sorted(seams.items(), key=lambda kv: -kv[1]["max_n_mm"]))
    crit = min(seams.items(), key=lambda kv: kv[1]["sf"])
    out["seam_critical"] = {"seam": crit[0], **crit[1]}
    # attachments
    att = {}
    for c in cab.cables:
        T = c.tension(x)
        cap = c.meta.get("capacity_n")
        att[c.name] = {"kind": c.kind, "tension_n": _f(T, 1), "webbing": c.material_id, "capacity_n": cap,
                       "sf_capacity": _f(cap / T, 1) if cap and T > 1e-6 else None,
                       "sf_webbing_break": _f(c.meta["break_n"] / T, 0) if T > 1e-6 else None,
                       "length_mm": _f(c.length(x), 0), "mode": c.meta.get("mode")}
    hp = sim.term("hinge_pins")
    if hp is not None:
        for nm, f in zip(("hinge_R", "hinge_L"), hp.forces(x)):
            T = float(np.linalg.norm(f))
            cap = pm.scen["attachments"]["hinge"].get("capacity_n")
            att[nm] = {"kind": "hinge", "tension_n": _f(T, 1), "webbing": pm.scen["attachments"]["hinge"]["webbing"],
                       "capacity_n": cap, "sf_capacity": _f(cap / T, 1) if cap and T > 1e-6 else None,
                       "force_xyz_n": [_f(v, 1) for v in f], "mode": "pin"}
    out["attachments"] = att
    # contact with the spreader and the frame
    cont = {}
    for nm in ("contact_spreader", "contact_frame"):
        t = sim.term(nm)
        idx, f = t.forces(x)
        cont[nm] = {"nodes": int(len(idx)), "force_n": [_f(v, 1) for v in f.sum(0)],
                    "force_total_n": _f(np.linalg.norm(f.sum(0)), 1)}
    b01 = pm.nodes_of("B-01")
    X0 = m.X0
    foot = b01[(np.abs(X0[b01, 0]) <= SPREADER["x_half"] - 10) & (X0[b01, 2] > SPREADER["z"][0] + 10)
               & (X0[b01, 2] < SPREADER["z"][1] - 10)]
    gap = sim.term("contact_spreader").gap(x, foot)
    clr = pm.scen["contact"]["clearance"]
    va = np.bincount(m.tris.ravel(), np.repeat(tm["area"] / 3, 3), minlength=m.n)
    touching = gap < clr + 1.0
    sp_area = 2 * SPREADER["x_half"] * (SPREADER["z"][1] - SPREADER["z"][0])
    fs = cont["contact_spreader"]["force_total_n"]
    a_c = float(va[foot][touching].sum())
    cont["spreader_footprint"] = {"b01_nodes": int(len(foot)), "touching_pct": _f(touching.mean() * 100, 0),
                                  "contact_area_cm2": _f(a_c / 100, 0), "spreader_area_cm2": _f(sp_area / 100, 0),
                                  "mean_pressure_kpa": _f(fs / max(a_c, 1) * 1e3, 2),
                                  "max_gap_mm": _f(gap.max(), 1), "median_gap_mm": _f(np.median(gap), 1)}
    # initial interference of the drafted bag with the spreader (design check)
    g0 = sim.term("contact_spreader").f(X0[b01])[0]
    out["drafted_vs_spreader"] = {"min_gap_mm": _f(g0.min(), 1), "nodes_inside": int((g0 < 0).sum())}
    out["contact"] = cont
    # profile
    sec = np.abs(x[:, 0]) < 0.6 * pm.h
    zb = np.arange(pm.c["Z0"], x[:, 2].max(), 50.0)
    depth = []
    for z in zb:
        s_ = np.abs(x[:, 2] - z) < 25
        if s_.sum() > 3:
            depth.append([_f(z, 0), _f(x[s_, 1].min(), 1), _f(x[s_, 1].max(), 1), _f(x[s_, 0].min(), 1), _f(x[s_, 0].max(), 1)])
    out["profile"] = {"depth_by_z": depth, "floor_min_z_mm": _f(x[:, 2].min(), 1),
                      "floor_drop_mm": _f(pm.c["Z0"] - x[pm.nodes_of("B-05"), 2].min(), 1),
                      "max_depth_aft_mm": _f(x[:, 1].max(), 1), "drafted_max_depth_mm": _f(X0[:, 1].max(), 1),
                      "top_z_mm": _f(x[:, 2].max(), 0),
                      "section_x0_segments_yz": [[[_f(p[1], 1), _f(p[2], 1)] for p in sg] for sg in slice_x(x, m.tris)]}
    out["tri_e_max"] = tm["e_max"]
    out["tri_wrinkle"] = tm["e_min"] < WRINKLE_STRAIN
    return out


def slice_x(x, tris, x0=0.0):
    """Segments (k, 2, 3) where the plane x = x0 cuts the mesh (mid-plane profile)."""
    P = x[tris]
    d = P[:, :, 0] - x0
    segs = []
    for t in np.where((d.min(1) < 0) & (d.max(1) > 0))[0]:
        pts = []
        for i in range(3):
            j = (i + 1) % 3
            if d[t, i] * d[t, j] < 0:
                w = d[t, i] / (d[t, i] - d[t, j])
                pts.append(P[t, i] + w * (P[t, j] - P[t, i]))
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs)


def to_json(d):
    def conv(o):
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items() if not k.startswith("tri_")}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        return o
    return conv(d)


# ============================================================================ plots
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def shrink_png(path: Path, max_bytes: int = 1_500_000):
    from PIL import Image
    if path.stat().st_size <= max_bytes:
        return
    im = Image.open(path).convert("RGB")
    im.save(path, optimize=True)
    if path.stat().st_size > max_bytes:
        im.quantize(colors=256).save(path, optimize=True)


def plot_validation(val: dict, path: Path):
    plt = _plt()
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.6))
    c = val["cylinder"]
    labels = ["hoop\n(p r)", "axial\n(p r/2)", "long seam\n(p r)", "cap seam\n(p r/2)"]
    sim = [c["hoop"], c["axial"], c["seam_long"], c["seam_cap"]]
    ex = [c["hoop_exact"], c["axial_exact"], c["hoop_exact"], c["axial_exact"]]
    xx = np.arange(4)
    ax[0].bar(xx - 0.18, ex, 0.36, color="#9aa0a6", label="exact")
    ax[0].bar(xx + 0.18, sim, 0.36, color="#3b6ea8", label="sim")
    for i in range(4):
        ax[0].text(xx[i] + 0.18, sim[i], f"{(sim[i] / ex[i] - 1) * 100:+.1f}%", ha="center", va="bottom", fontsize=9)
    ax[0].set_xticks(xx, labels)
    ax[0].set_ylabel("membrane / seam line force, N/mm")
    ax[0].set_title(f"Inflated cylinder R {c['R']:.0f}, p {c['p'] * 1e3:.0f} kPa")
    ax[0].legend(frameon=False, loc="lower right")
    k = val["catenary"]
    ax[1].plot(k["xs"], k["z_exact"], color="#9aa0a6", lw=5, label="catenary (exact)")
    ax[1].plot(k["xs"], k["z_sim"], color="#3b6ea8", lw=1.6, label="sim")
    ax[1].set_aspect("equal")
    ax[1].set_title(f"Hanging sheet: sag {k['sag']:.1f} vs {k['sag_exact']:.1f} mm\nH {k['H'] * 1e3:.3f} vs {k['H_exact'] * 1e3:.3f} N/m")
    ax[1].set_xlabel("x, mm")
    ax[1].legend(frameon=False, loc="lower center")
    a = val["area"]
    names = ["drape sheet\n3D / flat", "bag (meat)\nsewn / flat", "mesher\ntri / polygon"]
    vals = [a["drape_ratio"], a.get("bag_ratio", np.nan), a["mesher_ratio"]]
    ax[2].bar(range(3), [(v - 1) * 100 for v in vals], color=["#3b6ea8", "#c4722b", "#3b6ea8"])
    for i, v in enumerate(vals):
        ax[2].text(i, (v - 1) * 100, f"{(v - 1) * 100:+.2f}%", ha="center", va="bottom" if v >= 1 else "top")
    ax[2].axhline(0, color="k", lw=0.8)
    ax[2].set_xticks(range(3), names)
    ax[2].set_ylabel("area change, %")
    ax[2].set_title("Flat-pattern area conserved", pad=14)
    fig.suptitle("Cloth solver validation against closed-form answers", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    shrink_png(path)


def _tri_collection(ax, x, tris, vals, i, j, depth_axis, depth_sign, cmap, vmin, vmax):
    from matplotlib.collections import PolyCollection
    P = x[tris]
    order = np.argsort(depth_sign * P[:, :, depth_axis].mean(1))
    pc = PolyCollection(P[order][:, :, [i, j]], array=vals[order], cmap=cmap, edgecolors="face", linewidths=0.2)
    pc.set_clim(vmin, vmax)
    ax.add_collection(pc)
    ax.autoscale_view()
    ax.set_aspect("equal")
    return pc


def plot_strain_views(pm, res: dict, x: np.ndarray, path: Path, title: str):
    plt = _plt()
    m = pm.mesh
    e = res["tri_e_max"] * 100
    vmax = max(1.0, float(np.percentile(e, 99.5)))
    fig, ax = plt.subplots(1, 3, figsize=(14, 7.5))
    cl = pm.clouds
    views = [("side (from wearer's right)", 1, 2, 0, -1), ("outer face (from behind)", 0, 2, 1, -1),
             ("frame side (wearer's view)", 0, 2, 1, 1)]
    for a, (nm, i, j, d, sg) in zip(ax, views):
        if nm.startswith("frame"):
            fr = cl["frame_V"]
            a.scatter(fr[:, i], fr[:, j], s=0.2, c="#2d2d2d", zorder=3)
        pc = _tri_collection(a, x, m.tris, e, i, j, d, sg if d != 0 else 1, "turbo", 0, vmax)
        if nm.startswith("side"):
            fr = cl["frame_V"]
            a.scatter(fr[:, i], fr[:, j], s=0.2, c="#2d2d2d", zorder=0)
        a.set_title(nm)
        a.set_xlabel("y aft, mm" if i == 1 else "x, mm")
    ax[0].set_ylabel("z, mm")
    if nm.startswith("frame"):
        ax[2].invert_xaxis()
    cb = fig.colorbar(pc, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("max principal strain, %")
    fig.suptitle(title, fontweight="bold")
    fig.savefig(path, dpi=95, bbox_inches="tight")
    plt.close(fig)
    shrink_png(path)


def plot_seams(results: dict, path: Path, top=14):
    plt = _plt()
    cases = list(results)
    ref = results[cases[-1]]["seams"]
    names = list(ref)[:top]
    fig, ax = plt.subplots(figsize=(11, 0.45 * len(names) + 2.2))
    yy = np.arange(len(names))
    w = 0.8 / len(cases)
    cols = {"empty": "#9aa0a6", "fill": "#3b6ea8", "meat": "#c4722b"}
    for k, c in enumerate(cases):
        v = [results[c]["seams"].get(n, {}).get("max_n_mm", 0) for n in names]
        ax.barh(yy + (k - (len(cases) - 1) / 2) * w, v, w, color=cols.get(c, None), label=c)
    for i, n in enumerate(names):
        st, sf = ref[n]["strength_n_mm"], ref[n]["sf"]
        ax.text(max(results[c]["seams"].get(n, {}).get("max_n_mm", 0) for c in cases) * 1.02, i,
                f"SF {sf:.0f}  (strength {st:.0f} N/mm)", va="center", fontsize=8.5)
    ax.set_yticks(yy, names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("peak seam line force, N/mm (welded-node force / tributary length; seam ends and attachments excluded)")
    ax.set_title("Seam line force per seam, all load cases (SF vs thread/fabric seam strength, meat case)", fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    xm = ax.get_xlim()[1]
    ax.set_xlim(0, xm * 1.35)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    shrink_png(path)


def plot_profiles(pm, xs: dict, sweep: list, path: Path):
    plt = _plt()
    fig, ax = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1.25, 1]})
    cl = pm.clouds
    fr = cl["frame_V"]
    ax[0].scatter(fr[:, 1], fr[:, 2], s=0.3, c="#555555", label="frame")
    sp = cl["spreader_V"]
    ax[0].scatter(sp[:, 1], sp[:, 2], s=0.3, c="#8e44ad", label="spreader")
    cols = {"drafted": "#222222", "empty": "#9aa0a6", "fill": "#3b6ea8", "meat": "#c4722b"}
    m = pm.mesh
    from matplotlib.collections import LineCollection
    for nm, x in [("drafted", m.X0)] + list(xs.items()):
        sg = slice_x(x, m.tris)[:, :, 1:]
        lc = LineCollection(sg, colors=cols.get(nm), linewidths=2.2 if nm != "drafted" else 1.0,
                            linestyles="solid" if nm != "drafted" else "dashed", label=nm)
        ax[0].add_collection(lc)
    ax[0].autoscale_view()
    ax[0].set_aspect("equal")
    ax[0].set_xlabel("y aft of the frame, mm")
    ax[0].set_ylabel("z, mm")
    ax[0].set_title("Mid-plane profile (x = 0), wearer on the left")
    ax[0].legend(frameon=False, loc="upper left", markerscale=10, fontsize=9)
    if sweep:
        p = [s["p0_kpa"] for s in sweep]
        v = [s["closed_L"] for s in sweep]
        vb = [s["body_L"] for s in sweep]
        ax[1].plot(p, v, "o-", color="#3b6ea8", label="closed bag (to the fill line)")
        ax[1].plot(p, vb, "s-", color="#c4722b", label="body below the collar seam")
        ax[1].axhline(pm.c["design_volume_L"], color="k", ls="--", lw=1)
        ax[1].text(p[0], pm.c["design_volume_L"] + 0.3, f"design {pm.c['design_volume_L']:.1f} L", fontsize=9)
        ax[1].set_xlabel("inflation pressure, kPa (no weight)")
        ax[1].set_ylabel("volume, L")
        ax[1].set_title("Sewn-bag volume vs packing pressure")
        ax[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    shrink_png(path)


def diff_tables(a: dict, b: dict) -> str:
    """Markdown before/after table for two results.json dicts."""
    lines = [f"# Cloth-sim diff: `{a.get('scenario')}` -> `{b.get('scenario')}`", ""]
    for case in [c for c in a["cases"] if c in b["cases"]]:
        A, B = a["cases"][case], b["cases"][case]
        lines += [f"## {case}", "", "| quantity | before | after | change |", "|---|---:|---:|---:|"]

        def row(lbl, va, vb, unit=""):
            if va is None or vb is None:
                return
            d = vb - va
            pc = f" ({d / va * 100:+.1f} %)" if va else ""
            lines.append(f"| {lbl} | {va:.3g}{unit} | {vb:.3g}{unit} | {d:+.3g}{unit}{pc} |")
        row("closed volume, L", A["volume"]["closed_L"], B["volume"]["closed_L"])
        row("body volume, L", A["volume"]["body_below_collar_seam_L"], B["volume"]["body_below_collar_seam_L"])
        row("max depth aft, mm", A["profile"]["max_depth_aft_mm"], B["profile"]["max_depth_aft_mm"])
        row("floor drop, mm", A["profile"]["floor_drop_mm"], B["profile"]["floor_drop_mm"])
        for p in A["pieces"]:
            if p in B["pieces"]:
                row(f"{p} strain p99, %", A["pieces"][p]["e_p99_pct"], B["pieces"][p]["e_p99_pct"])
                row(f"{p} wrinkle area, %", A["pieces"][p]["wrinkle_area_pct"], B["pieces"][p]["wrinkle_area_pct"])
        for s in A["seams"]:
            if s in B["seams"]:
                row(f"seam {s.replace('|', '\\|')}, N/mm", A["seams"][s]["max_n_mm"], B["seams"][s]["max_n_mm"])
        for t in A["attachments"]:
            if t in B["attachments"]:
                row(f"{t} tension, N", A["attachments"][t]["tension_n"], B["attachments"][t]["tension_n"])
        lines.append("")
    return "\n".join(lines)


def plot_diff(a: dict, b: dict, path: Path, case="meat"):
    """Before/after bars for one case: volume, strain p99 per piece, peak seam forces."""
    plt = _plt()
    A, B = a["cases"][case], b["cases"][case]
    fig, ax = plt.subplots(1, 3, figsize=(15, 6), gridspec_kw={"width_ratios": [0.6, 1.4, 1.6]})
    lab = [a.get("scenario", "before"), b.get("scenario", "after")]
    v = [[A["volume"]["closed_L"], B["volume"]["closed_L"]],
         [A["volume"]["body_below_collar_seam_L"], B["volume"]["body_below_collar_seam_L"]]]
    xx = np.arange(2)
    for k, c in enumerate(("#9aa0a6", "#3b6ea8")):
        ax[0].bar(xx + (k - 0.5) * 0.38, [v[0][k], v[1][k]], 0.38, color=c, label=lab[k])
    ax[0].set_xticks(xx, ["closed", "body"])
    ax[0].set_ylabel("volume, L")
    ax[0].set_ylim(0, max(v[0]) * 1.15)
    for i in range(2):
        ax[0].text(i, max(v[i]) * 1.02, f"{v[i][1] - v[i][0]:+.2f} L", ha="center")
    ax[0].legend(frameon=False, fontsize=8, loc="lower center")
    ps = [p for p in A["pieces"] if p in B["pieces"]]
    yy = np.arange(len(ps))
    ax[1].barh(yy - 0.2, [A["pieces"][p]["warp_max_pct"] for p in ps], 0.4, color="#9aa0a6", label=f"{lab[0]} warp max")
    ax[1].barh(yy + 0.2, [B["pieces"][p]["warp_max_pct"] for p in ps], 0.4, color="#3b6ea8", label=f"{lab[1]} warp max")
    ax[1].set_yticks(yy, ps)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("max warp strain, %")
    ax[1].legend(frameon=False, fontsize=8)
    ss = [s_ for s_ in list(A["seams"])[:10] if s_ in B["seams"]]
    yy = np.arange(len(ss))
    ax[2].barh(yy - 0.2, [A["seams"][s_]["max_n_mm"] for s_ in ss], 0.4, color="#9aa0a6", label=lab[0])
    ax[2].barh(yy + 0.2, [B["seams"][s_]["max_n_mm"] for s_ in ss], 0.4, color="#3b6ea8", label=lab[1])
    ax[2].set_yticks(yy, ss, fontsize=9)
    ax[2].invert_yaxis()
    ax[2].set_xlabel("peak seam line force, N/mm")
    ax[2].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Panel adjustment, before / after ('{case}' case)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    shrink_png(path)


# ============================================================================ GLB + viewer
def export_viewer(pm, res: dict, x: np.ndarray, sim, out_dir: Path, tag: str, title: str) -> dict:
    import trimesh
    from matplotlib import colormaps
    from trimesh.visual import ColorVisuals
    from trimesh.visual.material import PBRMaterial
    from trimesh.visual import TextureVisuals

    from huntkit.viz3d.export import FLIP_WINDING, dedupe_glb, to_gltf
    from huntkit.viz3d.viewer import build_html
    m = pm.mesh
    e = res["tri_e_max"] * 100
    vmax = max(1.0, float(np.percentile(e, 99.5)))
    va = np.bincount(m.tris.ravel(), np.repeat(e, 3), minlength=m.n) / np.maximum(np.bincount(m.tris.ravel(), minlength=m.n), 1)
    rgba = (colormaps["turbo"](np.clip(va / vmax, 0, 1)) * 255).astype(np.uint8)
    scene = trimesh.Scene()

    def add(name, V, F, colors=None, mat=None):
        tm = trimesh.Trimesh(vertices=to_gltf(V), faces=(F[:, ::-1] if FLIP_WINDING else F).copy(), process=False)
        if colors is not None:
            tm.visual = ColorVisuals(tm, vertex_colors=colors)
        else:
            tm.visual = TextureVisuals(uv=np.zeros((len(V), 2)), material=mat)
        scene.add_geometry(tm, node_name=name, geom_name=name)
    # double-sided look: add the inside as a second, darker shell
    add("clothsim_bag", x, m.tris, rgba)
    clay = PBRMaterial(name="clay", baseColorFactor=[0.32, 0.32, 0.33, 1.0], metallicFactor=0.0, roughnessFactor=0.7)
    carb = PBRMaterial(name="clay", baseColorFactor=[0.05, 0.05, 0.06, 1.0], metallicFactor=0.0, roughnessFactor=0.5)
    add("clothsim_frame", pm.clouds["frame_V"], pm.clouds["frame_F"], mat=clay)
    add("clothsim_spreader", pm.clouds["spreader_V"], pm.clouds["spreader_F"], mat=carb)
    web = PBRMaterial(name="webbing", baseColorFactor=[0.62, 0.55, 0.40, 1.0], metallicFactor=0.0, roughnessFactor=0.8)
    segs = []
    for c in sim.term("cables").cables:
        P = c.points(x)
        for a, b in zip(P[:-1], P[1:]):
            if np.linalg.norm(b - a) > 1:
                segs.append(trimesh.creation.cylinder(radius=4.0, segment=[a, b], sections=6))
    if segs:
        st = trimesh.util.concatenate(segs)
        add("clothsim_straps", st.vertices, st.faces, mat=web)
    glb = out_dir / f"clothsim_{tag}.glb"
    glb.write_bytes(dedupe_glb(trimesh.exchange.gltf.export_glb(scene, include_normals=True)))
    parts = {n: {"group": "bag", "torso": None, "modes": ["pack", "frame"], "variant": None, "material": "",
                 "label": n, "explode": [0, 0, 0], "haul": [0, 0, 0]}
             for n in ("clothsim_bag", "clothsim_frame", "clothsim_spreader", "clothsim_straps")}
    v = res["volume"]
    sc = res["seam_critical"]
    metrics = {"chips": [f"Volume <b>{v['closed_L']:.1f} L</b> closed at the fill line",
                         f"Strain colour 0 to <b>{vmax:.1f} %</b> (turbo: blue low, red high)",
                         f"Critical seam <b>{sc['seam']}</b>: {sc['max_n_mm']:.2f} N/mm, SF {sc['sf']:.0f}",
                         f"Spreader contact <b>{res['contact']['contact_spreader']['force_total_n']:.0f} N</b>"],
               "subtitle": title, "torsos": {}}
    html = build_html(glb, parts, metrics, {}, out_dir / f"clothsim_{tag}_viewer.html", title=f"Cloth sim: {tag}")
    return {"glb": glb, "html": html, "vmax": vmax}


def render_viewer(html: Path, shots: list, width=900, height=900) -> list:
    import os
    import subprocess
    import tempfile
    render_js = Path(__file__).resolve().parents[1] / "viz3d" / "render.js"
    cfg = {"html": str(Path(html).resolve()), "width": width, "height": height, "scale": 1.5, "shots": shots}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(cfg, tf)
    subprocess.run(["node", str(render_js), tf.name], check=True, capture_output=True,
                   env={**os.environ, "NODE_PATH": "/opt/node22/lib/node_modules"}, timeout=300)
    out = []
    for s in shots:
        p = Path(s["file"])
        if p.exists():
            shrink_png(p)
            out.append(p)
    return out
