"""Write the generative-design deliverables: renders, print README, results YAML, design doc."""
from __future__ import annotations

import pickle
import shutil
from pathlib import Path

import numpy as np
import trimesh
import yaml

from huntkit.fea.materials_bridge import REPO_ROOT, get_material

from . import render
from .cli import ANALYSIS, DATE, PRINT, SCREENS, WORK, screen

LUG_ORDER = ["crown_corner", "stay_hub", "lumbar_elbow", "stay_foot", "hip_pivot_mount"]
G_LB = 453.592


def _mesh(name, variant, printed=False):
    d = pickle.load(open(WORK / f"{name}_{variant}_mesh.pkl", "rb"))
    k = "printed" if printed else "mesh"
    return trimesh.Trimesh(d[k + "_v"], d[k + "_f"], process=False)


def _f(x, nd=1):
    if x is None:
        return "-"
    if isinstance(x, (float, np.floating)) and not np.isfinite(x):
        return "inf"
    return f"{x:.{nd}f}"


def bond_compare(results) -> list[dict]:
    """Bonded-socket check (huntkit.fea.joints.bond_check) for printed Ti 1.0 mm sleeves vs the 7075 2.0 mm
    sleeves, worst load set per lug socket (factored)."""
    from huntkit.fea.joints import bond_check, tube_wall_stiffness
    from huntkit.fea.sections import from_spec
    frame = results["frame"]
    res0, m0, _ = next(iter(frame["runs"].values()))
    jp = dict(m0["params"].get("joint") or {})
    secs = {}
    for mm in m0["members"]:
        s = from_spec(mm["section"])
        if getattr(s, "composite", False) and "od" in s.dims:
            secs.setdefault(round(s.dims["od"], 1), s)
    out = []
    for sp in results["specs"]:
        for s in sp.sockets:
            if s.kind not in ("end", "through") or not s.loads:
                continue
            sec = secs.get(round(s.od, 1))
            if sec is None:
                continue
            Et, Gt = tube_wall_stiffness(sec)
            worst = {}
            for label, mat, ts in (("7075 2.0 mm", "alu_7075_t6", jp.get("sleeve_t_mm", 2.0)),
                                   ("SLM Ti 1.0 mm", "ti_6al_4v_slm", 1.0)):
                best = None
                for key, v in s.loads.items():
                    req = sp.case_req.get(key, 1.0)
                    a = s.axis
                    N = float(v[:3] @ a); T = float(v[3:] @ a)
                    Mv = v[3:] - T * a
                    M = float(np.linalg.norm(Mv))
                    prm = {**jp, "sleeve_material": mat, "sleeve_t_mm": ts, "cfrp_adherend": True}
                    if s.kind == "through":
                        prm["overlap_mm"] = jp.get("through_overlap_mm", 40.0)
                    br = bond_check(N, T, M, s.od / 2, Et, Gt, prm)
                    r = {"key": key, "sf_avg_over_req": br.sf_avg / req, "sf_peak": br.sf_peak,
                         "k_peak": br.k_axial}
                    if best is None or r["sf_avg_over_req"] < best["sf_avg_over_req"]:
                        best = r
                worst[label] = best
            out.append({"lug": sp.name, "socket": s.name, **{k: v for k, v in worst.items()}})
    return out


def collar_check(results) -> dict:
    """Stay-top collar (crown-leg bushing seat): ring bending 6 m / t^2 with m = 0.318 (F_r / L_b) R_m
    (huntkit.fea.pack5200.crown_checks method), printed Ti thickness picked for SF/req >= 1."""
    frame = results["frame"]
    Fr_max, key = 0.0, None
    Lb, od = 70.0, 25.0
    for (case, t), (res, model, cs) in frame["runs"].items():
        lf = res.meta.get("link_forces", {})
        Lb = float(model["params"].get("bushing_len_mm", 70.0))
        from huntkit.fea.sections import from_spec
        st = from_spec(next(mm for mm in model["members"] if mm["group"].startswith("stay_upper"))["section"])
        od = st.dims["od"]
        for n in ("bush_top_L", "bush_top_R"):
            f = lf.get(n)
            if f is None:
                continue
            Fr = float(np.hypot(f[0], f[1])) * cs.required_sf
            if Fr > Fr_max:
                Fr_max, key = Fr, f"{case}|{t}|{n}"
    allow = float(get_material("ti_6al_4v_slm").require("yield_strength_design_mpa"))
    tc = 1.0
    while True:
        Rm = od / 2 + 0.5 + tc / 2
        sig = 6 * 0.318 * (Fr_max / Lb) * Rm / tc ** 2
        if sig <= allow or tc > 3:
            break
        tc = round(tc + 0.1, 2)
    L = 30.0 + 5.0
    m_ti = np.pi * (od + 1.0 + tc) * tc * L * 4430e-6
    from .lugs import sleeve_7075_g
    return {"Fr_factored_n": Fr_max, "key": key, "t_ti_mm": tc, "sigma_mpa": sig, "sf": allow / sig,
            "mass_ti_g": m_ti, "mass_7075_g": sleeve_7075_g(od, 30.0), "qty": 2}


def write_all(results, log=print):
    SCREENS.mkdir(parents=True, exist_ok=True)
    (PRINT / "cut").mkdir(parents=True, exist_ok=True)
    lugs = {(r["name"], r["variant"]): r for r in results["lugs"]}
    specs = {s.name: s for s in results["specs"]}
    shots = []
    names = [n for n in LUG_ORDER if (n, "slm_ti") in lugs]
    # ---------------------------------------------------------------- 1-5 lug cards
    for i, n in enumerate(names, 1):
        rs, rf = lugs[(n, "slm_ti")], lugs.get((n, "fdm_pacf"))
        ms = _mesh(n, "slm_ti")
        mf = _mesh(n, "fdm_pacf") if rf else None
        lines = [f"{rs['title']}", f"qty {rs['qty']} per frame (left = mirrored file)", "",
                 f"SLM Ti-6Al-4V + HIP: {rs['mass_g']:.1f} g each",
                 f"  7075 baseline: {rs['baseline_7075_g']:.1f} g each",
                 f"  strength SF/required {_f(rs['sf_static'], 1)}",
                 f"  fatigue SF {_f((rs['fatigue'] or {}).get('sf'), 1)} (as-built + HIP)",
                 f"  min wall {rs['min_feature_mm']:.1f} mm, build {rs['orientation']['best']}",
                 f"  ~${rs['cost_ti_usd']:.0f} each (incl. HIP + reaming)"]
        if rf:
            lines += ["", f"FDM PAHT-CF: {rf['mass_g']:.1f} g, SF/req {_f(rf['sf_static'], 1)}",
                      f"  layers normal to {rf['layer_normal']}, {rf['fdm_hours']:.1f} h, ${rf['fdm_usd']:.2f}"]
        p = render.lug_card(ms, mf, f"Lug {i}: {n.replace('_', ' ')}", lines, screen(i))
        shots.append((p, f"{n} lug render"))
    k = len(names) + 1
    # ---------------------------------------------------------------- plate
    plates = results["plates"]
    ok = [p for p in plates if p["ok"]]
    pbest = min(ok, key=lambda p: p["mass_g"]) if ok else max(plates, key=lambda p: p["chk"]["min_sf_combined"])
    base_plate_g = 250 * 140 * 4.0 * float(get_material("cfrp_plate_quasi_iso").require("density_kg_m3")) * 1e-6
    dxf_path = PRINT / "cut" / f"lumbar_plate_qi_t{pbest['t']:g}_cut.dxf"
    shutil.copy(pbest["dxf"]["path"], dxf_path)
    p = render.plate_card(pbest["pp"], pbest["solid"], pbest["dxf"], pbest["chk"], pbest["rep"], pbest["mass_g"],
                          base_plate_g, screen(k))
    shots.append((p, "lumbar plate cut pattern")); k += 1
    # ---------------------------------------------------------------- layout
    lay = results["layout"]
    lp = lay["lp"]
    variants = []
    for name, gs in lp.items():
        variants.append({"name": name, "lp_mass_g": max(gs[t]["mass_g"] for t in gs)})
    p = render.layout_card(lp["free ground structure"], lp["current"], variants, screen(k), torso=19)
    shots.append((p, "layout optimization")); k += 1
    # ---------------------------------------------------------------- mass chart
    coll = collar_check(results)
    rows = []
    tot_base = tot_new = tot_fdm = 0.0
    for n in names:
        rs, rf = lugs[(n, "slm_ti")], lugs.get((n, "fdm_pacf"))
        q = rs["qty"]
        rows.append((f"{n.replace('_', ' ')} x{q}", rs["baseline_7075_g"] * q, rs["mass_g"] * q,
                     rf["mass_g"] * q if rf else None))
    rows.append((f"stay-top collar x2", coll["mass_7075_g"] * 2, coll["mass_ti_g"] * 2, None))
    rows.append(("lumbar plate", base_plate_g, pbest["mass_g"], None))
    for r in rows:
        tot_base += r[1]; tot_new += r[2]
    p = render.mass_chart(rows, screen(k), f"v1 frame hardware: {tot_base:.0f} g -> {tot_new:.0f} g "
                                           f"({tot_new - tot_base:+.0f} g)")
    shots.append((p, "mass comparison")); k += 1
    # ---------------------------------------------------------------- build plate (FDM prototype set)
    parts = []
    for n in names:
        if (n, "fdm_pacf") in lugs:
            m = _mesh(n, "fdm_pacf", printed=True)
            q = lugs[(n, "fdm_pacf")]["qty"]
            for j in range(q):
                mm = m.copy()
                if j % 2 == 1 and q > 1:      # left-hand parts are mirrored
                    mm.apply_scale([-1, 1, 1]); mm.invert(); mm.apply_translation(-mm.bounds[0])
                parts.append((mm, n.replace("_", " ")))
    for pr in results["printables"]:
        m = pr["mesh_fdm"].copy()
        if pr["name"] == "crown_rack":
            m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))   # teeth up, flat
        m.apply_translation(-m.bounds[0])
        for _ in range(pr["qty"]):
            parts.append((m.copy(), pr["name"].replace("_", " ")))
    parts.sort(key=lambda x: -x[0].extents[0])
    p, placed = render.build_plate(parts, screen(k), title="Full FDM prototype frame set, Bambu Lab H2S plate (PAHT-CF)")
    shots.append((p, "FDM build plate")); k += 1
    # ---------------------------------------------------------------- SIMP verification
    p = simp_verification_png(results, screen(k))
    shots.append((p, "SIMP benchmark + convergence")); k += 1
    # ---------------------------------------------------------------- docs
    bonds = bond_compare(results)
    summary = summarize(results, names, lugs, pbest, base_plate_g, coll, rows, tot_base, tot_new, bonds)
    (ANALYSIS / "gendesign_results.yaml").write_text(
        "# GENERATED by python -m huntkit.gendesign.cli stage report - do not hand-edit\n"
        + yaml.safe_dump(_plain(summary), sort_keys=False, width=110))
    write_print_readme(results, names, lugs, pbest, dxf_path, coll)
    write_design_doc(results, names, lugs, pbest, base_plate_g, coll, rows, tot_base, tot_new, bonds, shots, summary)
    for p_, cap in shots:
        log(f"  screen: {p_}  ({cap})")
    return shots


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if np.isfinite(v) else str(v)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return _plain(x.tolist())
    return x


def simp_verification_png(results, path):
    import matplotlib.pyplot as plt
    from .simp import mbb_problem, run_simp
    render._style()
    r = run_simp(mbb_problem(120, 40, 0.5, 2.0), iters=100, beta_schedule=(0,))
    g = mbb_problem(120, 40).grid
    fig = plt.figure(figsize=(9, 11))
    ax = fig.add_axes([0.06, 0.72, 0.9, 0.2])
    x = g.to_array(r.xPhys).T
    full = np.hstack([x[:, ::-1], x])
    ax.imshow(1 - full, cmap="gray", origin="lower", vmin=0, vmax=1)
    ax.set_axis_off()
    ax.set_title(f"Benchmark: MBB beam (top88 setup, mirrored), c = {r.compliance:.1f}, vol {r.history[-1]['volume']:.3f}",
                 loc="left", fontsize=13)
    ax2 = fig.add_axes([0.12, 0.43, 0.83, 0.22])
    ax2.plot([h["it"] for h in r.history], [h["compliance"] for h in r.history], color=render.S1, lw=2)
    ax2.set_yscale("log"); ax2.set_xlabel("iteration"); ax2.set_ylabel("compliance")
    ax2.set_title("MBB compliance history (monotone decrease)", loc="left", fontsize=13)
    ax2.grid(color=render.GRID)
    ax3 = fig.add_axes([0.12, 0.06, 0.83, 0.28])
    cols = [render.S1, render.S2, render.S3, render.S4, "#e87ba4"]
    for i, lr in enumerate([l for l in results["lugs"] if l["variant"] == "slm_ti"]):
        c = np.array([h["c"] for h in lr["history"]])
        ax3.plot([h["it"] for h in lr["history"]], c / c[0], color=cols[i % 5], lw=2, label=lr["name"].replace("_", " "))
    ax3.set_yscale("log"); ax3.set_xlabel("iteration (final pass)"); ax3.set_ylabel("compliance / initial")
    ax3.legend(frameon=False, fontsize=10); ax3.grid(color=render.GRID)
    ax3.set_title("Lug SIMP convergence, final volume pass (beta 1-2-4-8 every 8 it;\nearly rise = start from uniform grey at a lower volume)", loc="left", fontsize=12)
    return render.save(fig, path)


def summarize(results, names, lugs, pbest, base_plate_g, coll, rows, tot_base, tot_new, bonds):
    lay = results["layout"]
    out = {"standard": results["frame"]["standard"], "fatigue_g": results["frame"]["fatigue_g"], "lugs": {},
           "plate": {}, "layout": {}, "frame_mass": {}}
    for n in names:
        for v in ("slm_ti", "fdm_pacf"):
            r = lugs.get((n, v))
            if not r:
                continue
            out["lugs"][f"{n}/{v}"] = {
                "qty": r["qty"], "mass_g": round(r["mass_g"], 1), "baseline_7075_g": round(r["baseline_7075_g"], 1),
                "volfrac": r["volfrac"], "sf_static_over_req": round(float(r["sf_static"]), 2),
                "governing": r["governing"], "fatigue_sf": round(float((r["fatigue"] or {}).get("sf", np.inf)), 2),
                "min_feature_mm": round(r["min_feature_mm"], 2), "orientation": r["orientation"]["best"],
                "support_area_mm2": round(r["orientation"]["support_area_mm2"], 0), "watertight": r["watertight"],
                "grid": r["grid"], "fine_h_mm": round(r["fine"]["h"], 3), "files": r["files"],
                "cost_ti_usd": None if r["cost_ti_usd"] is None else round(r["cost_ti_usd"], 0),
                "cost_al_usd": None if r["cost_al_usd"] is None else round(r["cost_al_usd"], 0),
                "fdm_hours": None if r["fdm_hours"] is None else round(r["fdm_hours"], 1),
                "fdm_usd": None if r["fdm_usd"] is None else round(r["fdm_usd"], 2),
                "layer_normal": r["layer_normal"], "passes": r["passes"]}
    out["stay_top_collar"] = {k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else v) for k, v in coll.items()}
    out["plate"] = {"t_mm": pbest["t"], "volfrac": pbest["vf"], "mass_g": round(pbest["mass_g"], 1),
                    "baseline_g": round(base_plate_g, 1), "n_cutouts": pbest["dxf"]["n_cutouts"],
                    "min_web_mm": round(pbest["rep"]["min_web_mm"], 1), "sf_combined": round(pbest["chk"]["min_sf_combined"], 2),
                    "sf_membrane": round(pbest["chk"]["min_sf_membrane"], 2), "sf_buckling": round(pbest["chk"]["min_sf_buckling"], 2),
                    "solid_ref_sf_combined": round(pbest["ref"]["min_sf_combined"], 2),
                    "all_options": [{"t": p["t"], "vf": p["vf"], "mass_g": round(p["mass_g"], 1), "ok": p["ok"],
                                     "sf_combined": round(p["chk"]["min_sf_combined"], 2),
                                     "sf_buckling": round(p["chk"]["min_sf_buckling"], 2)} for p in results["plates"]]}
    out["layout"] = {"lp_mass_g_worst_torso": {n: round(max(gs[t]["mass_g"] for t in gs), 1) for n, gs in lay["lp"].items()},
                     "discrete": [{"name": d["name"], "stay": (d["best"] or {}).get("stay"),
                                   "tubes_g": round(float((d["best"] or {}).get("tubes_g", np.nan)), 1),
                                   "brace_tubes_g": round(float((d["best"] or {}).get("brace_tubes_g", 0.0)), 1),
                                   "brace_lugs": d["brace_lugs"],
                                   "member_margin": round(float((d["best"] or {}).get("member_margin", np.nan)), 2),
                                   "buckling_margin": round(float((d["best"] or {}).get("buckling_margin", np.nan)), 2)}
                                  for d in lay["discrete"]]}
    out["frame_mass"] = {"replaced_items_baseline_g": round(tot_base, 1), "replaced_items_generative_g": round(tot_new, 1),
                         "delta_g": round(tot_new - tot_base, 1),
                         "rows": [{"item": r[0], "baseline_g": round(r[1], 1), "generative_g": round(r[2], 1),
                                   "fdm_g": None if r[3] is None else round(r[3], 1)} for r in rows]}
    out["bond_check"] = [{"lug": b["lug"], "socket": b["socket"],
                          **{k: {kk: (round(float(vv), 2) if not isinstance(vv, str) else vv) for kk, vv in v.items()}
                             for k, v in b.items() if isinstance(v, dict)}} for b in bonds]
    out["printables"] = [{k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else v) for k, v in p.items()
                          if k not in ("mesh_fdm", "check_slm", "check_fdm")} |
                         {"check_slm_sf": None if not p["check_slm"] else round(p["check_slm"]["sf_over_req"], 2),
                          "check_fdm_sf": None if not p["check_fdm"] else round(p["check_fdm"]["sf_over_req"], 2)}
                         for p in results["printables"]]
    return out


from .docs import write_design_doc, write_print_readme  # noqa: E402
