"""Generative design of the Pack 5200 carbon frame: lugs, lumbar plate, layout, printables.

    python -m huntkit.gendesign.cli run [--iters 36] [--procs 3] [--quick]
    python -m huntkit.gendesign.cli benchmark            # MBB / 3D cantilever SIMP benchmark + PNG

Writes designs/pack_5200/print/ (STL, 3MF, DXF, README), designs/pack_5200/analysis/generative_design.md
(+ gendesign_results.yaml) and outputs/screens/20261101_gendesign_<n>.png.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import time
from multiprocessing import get_context
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

from huntkit.fea.materials_bridge import REPO_ROOT, get_material  # noqa: E402

DESIGN = REPO_ROOT / "designs" / "pack_5200"
PRINT = DESIGN / "print"
ANALYSIS = DESIGN / "analysis"
SCREENS = REPO_ROOT / "outputs" / "screens"
WORK = REPO_ROOT / "outputs" / "gendesign"
DATE = "20261101"


def screen(n):
    return SCREENS / f"{DATE}_gendesign_{n}.png"


# ============================================================================ lugs (worker)
def lug_task(args):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    from . import surface
    from .lugs import (VARIANTS, lug_mesh, mass_g, optimize_lug, strength_check, verify_lug)
    from .printables import fdm_time_cost, slm_cost
    from .simp import min_feature_mm
    spec, variant, fatigue_g, iters = args
    cache = WORK / f"lug_{spec.name}_{variant}.pkl"
    if cache.exists():
        return pickle.load(open(cache, "rb"))
    t0 = time.time()
    var = VARIANTS[variant]
    vf = var["volfrac"]
    passes = []
    for k in range(3):
        opt = optimize_lug(spec, variant, volfrac=vf, iters=iters)
        ver = verify_lug(spec, variant, opt)
        chk = strength_check(spec, variant, ver, fatigue_g)
        sf_s = chk["min_sf_over_req"]
        sf_f = chk.get("fatigue", {}).get("sf", np.inf)
        sf = min(sf_s, sf_f)
        passes.append({"vf": vf, "opt": opt, "ver": ver, "chk": chk, "sf": sf})
        if variant == "slm_ti":
            if sf < 1.0:
                vf = min(0.5, vf * min(2.5, 1.3 / max(sf, 0.05)))
            elif sf > 4.0 and vf > 0.026 and not any(p["sf"] < 1.0 for p in passes):
                vf = max(0.025, vf * 0.5)      # min-gauge governed: walk the volume down
            else:
                break
        else:   # FDM prototype: aim for >= the full standard if cheap, cap the volume
            if sf < 1.0 and vf < 0.45:
                vf = min(0.45, vf * 1.6)
            elif sf > 6.0 and k == 0:
                vf = max(0.12, vf * 0.6)
            else:
                break
    ok = [p for p in passes if p["sf"] >= 1.0]
    best = min(ok, key=lambda p: p["vf"]) if ok else max(passes, key=lambda p: p["sf"])
    opt, ver, chk = best["opt"], best["ver"], best["chk"]
    mesh = lug_mesh(spec, variant, opt)
    m_g = mass_g(mesh, variant)
    solid = ver["grid"].to_array(ver["solid_mask"])
    tmin = min_feature_mm(solid, ver["grid"].h)
    stem = PRINT / ("lug_" + spec.name + ("_slm_ti" if variant == "slm_ti" else "_fdm_pacf"))
    if variant == "slm_ti":
        orient = surface.best_orientation(mesh, var["overhang_deg"])
        build_dir = surface.CANDIDATE_DIRS[orient["best"]]
    else:
        ax = chk["layer_normal"]
        cands = {k: v for k, v in surface.CANDIDATE_DIRS.items() if k[1] == ax}
        rows = {k: surface.overhang_area(mesh, v, var["overhang_deg"]) for k, v in cands.items()}
        bk = min(rows, key=rows.get)
        orient = {"best": bk, "support_area_mm2": rows[bk], "support_frac": rows[bk] / mesh.area, "by_dir": rows}
        build_dir = surface.CANDIDATE_DIRS[bk]
    printed = surface.orient_to(mesh, build_dir)
    files = surface.export(printed, stem)
    if spec.qty > 1 and any(s.name in ("stay", "lower", "leg", "plate_flange") for s in spec.sockets):
        mir = printed.copy()
        mir.apply_scale([-1, 1, 1]); mir.invert(); mir.apply_translation(-mir.bounds[0])
        files += surface.export(mir, stem.with_name(stem.name + "_LEFT"))
    bores = sum(1 for s in spec.sockets if s.kind in ("end", "through", "pin"))
    vol = abs(mesh.volume)
    cost = slm_cost(vol, bores, "ti") if variant == "slm_ti" else None
    al_cost = slm_cost(vol, bores, "al") if variant == "slm_ti" else None
    ftime, fcost = fdm_time_cost(vol) if variant != "slm_ti" else (None, None)
    hist = opt["simp"].history
    pickle.dump({"mesh_v": np.asarray(mesh.vertices), "mesh_f": np.asarray(mesh.faces),
                 "printed_v": np.asarray(printed.vertices), "printed_f": np.asarray(printed.faces)},
                open(WORK / f"{spec.name}_{variant}_mesh.pkl", "wb"))
    out = {"name": spec.name, "title": spec.title, "variant": variant, "qty": spec.qty, "note": spec.note,
            "baseline_7075_g": spec.baseline_7075_g, "mass_g": m_g, "volume_mm3": vol, "volfrac": best["vf"],
            "passes": [{"vf": p["vf"], "sf": p["sf"], "sf_static": p["chk"]["min_sf_over_req"],
                        "sf_fatigue": p["chk"].get("fatigue", {}).get("sf")} for p in passes],
            "sf_static": chk["min_sf_over_req"], "governing": chk["governing"], "fatigue": chk.get("fatigue"),
            "rows": [{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()} for r in chk["rows"]],
            "layer_normal": chk.get("layer_normal"), "allow": chk["allow"],
            "grid": {"shape": list(opt["grid"].shape), "h": opt["grid"].h, "ne": opt["grid"].ne,
                     "rmin_vox": opt["rmin_vox"]},
            "fine": {"h": ver["h_fine"], "n_solid": ver["n_solid_fine"]},
            "min_feature_mm": tmin, "orientation": {"best": orient["best"], "support_area_mm2": orient["support_area_mm2"],
                                                    "support_frac": orient["support_frac"]},
            "watertight": bool(printed.is_watertight), "files": [str(Path(f).relative_to(REPO_ROOT)) for f in files],
            "history": [{"it": h["it"], "c": h["compliance"], "vol": h["volume"], "beta": h["beta"]} for h in hist],
            "cases_opt": opt["keys"], "bores": bores, "cost_ti_usd": cost, "cost_al_usd": al_cost,
            "fdm_hours": ftime, "fdm_usd": fcost, "seconds": time.time() - t0}
    pickle.dump(out, open(cache, "wb"))
    return out


# ============================================================================ plate
PLATE_OPTIONS = ((4.0, 0.30), (4.0, 0.15), (3.0, 0.30), (3.0, 0.15))


def plate_task(opt):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    return run_plate(options=(opt,), log=print)[0]


def run_plate(options=PLATE_OPTIONS, log=print, tag=""):
    from .loads import run_all
    from .plate import build_plate_problem, check_plate, cleanup, optimize_plate, to_dxf, verify_plate
    out = []
    frames = {}
    for t, vf in options:
        cache = WORK / f"plate_{tag}t{t:g}_vf{vf:g}.pkl"
        if cache.exists():
            out.append(pickle.load(open(cache, "rb")))
            continue
        if t not in frames:
            frames[t] = run_all(log=None, lumbar_plate_t=t)
        fr = frames[t]
        pp = build_plate_problem(fr, h=1.25, t=t, volfrac=vf)
        r = optimize_plate(pp, iters=70)
        solid, rep = cleanup(pp, r.xPhys)
        ver = verify_plate(pp, solid)
        chk = check_plate(pp, solid, ver, fr)
        # solid-plate reference at the same thickness
        ref = check_plate(pp, np.ones_like(solid), verify_plate(pp, np.ones_like(solid)), fr)
        rho = float(get_material("cfrp_plate_quasi_iso").require("density_kg_m3"))
        dxf = to_dxf(pp, solid, WORK / f"plate_{tag}t{t:g}_vf{vf:g}.dxf")
        m = dxf["area_mm2"] * t * rho * 1e-6
        ok = chk["min_sf_combined"] >= 1.0 and chk["min_sf_buckling"] >= 1.5 and chk["min_sf_membrane"] >= 1.0
        log(f"  plate t={t:g} vf={vf:g}: {m:.0f} g, SF comb {chk['min_sf_combined']:.2f}, buck {chk['min_sf_buckling']:.1f}, "
            f"web {rep['min_web_mm']:.1f} mm, cut-outs {dxf['n_cutouts']}, ok={ok}")
        out.append({"t": t, "vf": vf, "mass_g": m, "chk": chk, "ref": ref, "rep": rep, "ok": ok, "pp": pp,
                    "solid": solid, "dxf": dxf, "simp": r})
        pickle.dump(out[-1], open(cache, "wb"))
    return out


# ============================================================================ layout
def run_layout(frame, log=print, quick=False):
    from huntkit.fea.sizing import section_spec
    from .layout import TOPOLOGIES, evaluate_topology, frame_ground_structure, model_bars
    torsos = (15, 19, 23)
    lp = {}
    variants = [("current", None), ("current + X upper bay", TOPOLOGIES["X_upper_bay"]),
                ("current + X lower bay", TOPOLOGIES["X_lower_bay"]),
                ("current + X both bays", TOPOLOGIES["X_both_bays"])]
    for name, extra in variants:
        gs = frame_ground_structure(frame, torsos=torsos, restrict=model_bars, extra=extra or ())
        lp[name] = gs
        log(f"  LP {name}: " + ", ".join(f"{t}: {gs[t]['mass_g']:.1f} g" for t in torsos))
    gs_full = frame_ground_structure(frame, torsos=torsos)
    lp["free ground structure"] = gs_full
    log("  LP free: " + ", ".join(f"{t}: {gs_full[t]['mass_g']:.1f} g" for t in torsos))
    # discrete check on buyable tubes
    from .loads import standard_cases
    cases, _, _ = standard_cases()
    stays = [dict(section_spec(("round", od), "RW45", k), _label=f"OD {od:g} RW45 k{k}")
             for od in (22.0, 25.0) for k in (3, 4, 6)]
    from huntkit.fea.sections import from_spec
    from huntkit.fea.sizing import make_section

    def lin_mass(spec):
        s = make_section({k: v for k, v in spec.items() if k != "_label"})
        return s.A * s.density_kg_m3
    stays.sort(key=lin_mass)
    brace = section_spec(("round", 16.0), "RW45", 3)
    disc = []
    for name, key in (("current", "current"), ("current + X upper bay", "X_upper_bay"),
                      ("current + X lower bay", "X_lower_bay")):
        best = None
        tried = []
        for st in stays:
            spec = {k: v for k, v in st.items() if k != "_label"}
            r = evaluate_topology({}, TOPOLOGIES[key], spec, None, brace, cases, torsos=torsos if not quick else (15, 23))
            tried.append({"stay": st["_label"],
                          "member_margin": r["member_margin"], "buckling_margin": r["buckling_margin"],
                          "tubes_g": r["tubes_g"], "governing": r["governing"]})
            if r["member_margin"] >= 1.0 and r["buckling_margin"] >= 1.0:
                best = {**r, "stay": tried[-1]["stay"]}
                break
        n_lugs = 0 if key == "current" else (len(TOPOLOGIES[key]) * 2 + len(TOPOLOGIES[key]) // 2)
        disc.append({"name": name, "best": best, "tried": tried, "brace_lugs": n_lugs})
        log(f"  discrete {name}: " + (f"stay {best['stay']}, tubes {best['tubes_g']:.0f} g" if best else "no passing stay"))
    return {"lp": lp, "discrete": disc}


# ============================================================================ printables
def run_printables(log=print):
    from . import surface
    from .printables import (fdm_time_cost, part_mass_g, rack_check, slm_cost, spring_pawl, toothed_rack,
                             webbing_guide)
    parts = []
    rack, info = toothed_rack()
    pawl_p, _ = spring_pawl(12.0)
    pawl_f, _ = spring_pawl(16.0)
    gfix, _ = webbing_guide(kind="fixed")
    gmov, _ = webbing_guide(kind="moving")
    req_lock = 1334.0 * 1.5     # geometry.yaml required compression capacity x 1.5 ultimate
    defs = [
        ("crown_rack", rack, rack, 1, "tier 1: AlSi10Mg SLM (heavier, 60 g); RECOMMENDED: PAHT-CF FDM or MJF PA12-GF / molded PA66-GF30 at volume", "alsi10mg_slm",
         rack_check("alsi10mg_slm", req_n=req_lock), rack_check("pa12_cf_fdm_paht", req_n=req_lock), "al", 2),
        ("crown_pawl", pawl_p, pawl_f, 1, "Ti-6Al-4V SLM + HIP", "ti_6al_4v_slm",
         rack_check("ti_6al_4v_slm", width=12.0, req_n=req_lock), rack_check("pa12_cf_fdm_paht", width=16.0, req_n=req_lock), "ti", 1),
        ("pulley_guide_fixed", gfix, gfix, 2, "tier 1: AlSi10Mg SLM; RECOMMENDED: PAHT-CF FDM (low load, 178 N tail tension); UHMWPE sleeve on the bar", "alsi10mg_slm", None, None, "al", 2),
        ("pulley_guide_moving", gmov, gmov, 1, "tier 1: AlSi10Mg SLM; RECOMMENDED: PAHT-CF FDM; UHMWPE sleeve on the bar", "alsi10mg_slm", None, None, "al", 0),
    ]
    for name, mp, mf, qty, proc, mat, chk_p, chk_f, metal, bores in defs:
        fp = surface.export(mp, PRINT / f"{name}_slm")
        ff = surface.export(mf, PRINT / f"{name}_fdm_pacf")
        hrs, usd = fdm_time_cost(abs(mf.volume))
        parts.append({"name": name, "qty": qty, "process": proc, "material": mat,
                      "mass_slm_g": part_mass_g(mp, mat), "mass_fdm_g": part_mass_g(mf, "pa12_cf_fdm_paht"),
                      "cost_slm_usd": slm_cost(abs(mp.volume), bores, metal), "fdm_hours": hrs, "fdm_usd": usd,
                      "check_slm": chk_p, "check_fdm": chk_f, "watertight": bool(mp.is_watertight and mf.is_watertight),
                      "files": [str(Path(f).relative_to(REPO_ROOT)) for f in fp + ff], "mesh_fdm": mf})
        log(f"  printable {name}: SLM {parts[-1]['mass_slm_g']:.1f} g, FDM {parts[-1]['mass_fdm_g']:.1f} g")
    return parts


# ============================================================================ main
def run_stage(stage, iters=36, procs=3, quick=False, log=print):
    """Run one stage with an on-disk cache (outputs/gendesign/): lugs | plate | layout | printables | report."""
    from .loads import run_all
    from .lugs import VARIANTS, build_specs
    for d in (PRINT, ANALYSIS, SCREENS, WORK):
        d.mkdir(parents=True, exist_ok=True)
    ctx = get_context("fork")
    if stage == "lugs":
        frame = run_all(log=log)
        specs = build_specs(frame)
        pickle.dump({"specs": specs, "standard": frame["standard"], "fatigue_g": frame["fatigue_g"]},
                    open(WORK / "stage_specs.pkl", "wb"))
        tasks = [(s, v, frame["fatigue_g"], iters) for s in specs for v in VARIANTS]
        with ctx.Pool(procs) as pool:
            for r in pool.imap_unordered(lug_task, tasks):
                log(f"  lug {r['name']}/{r['variant']}: {r['mass_g']:.1f} g, SF/req {r['sf_static']:.2f}, "
                    f"vf {r['volfrac']:.3f}, {r['seconds']:.0f} s")
    elif stage == "plate":
        with ctx.Pool(min(procs, len(PLATE_OPTIONS))) as pool:
            for r in pool.imap_unordered(plate_task, PLATE_OPTIONS):
                log(f"  plate t={r['t']:g} vf={r['vf']:g}: {r['mass_g']:.0f} g ok={r['ok']}")
    elif stage == "plate_v2":
        out = run_plate(options=((1.5, 0.30), (1.5, 0.20)), log=log, tag="v2_")
        pickle.dump(out, open(WORK / "stage_plate_v2.pkl", "wb"))
    elif stage == "layout":
        frame = run_all(log=None)
        lay = run_layout(frame, log, quick=quick)
        pickle.dump(lay, open(WORK / "stage_layout.pkl", "wb"))
    elif stage == "printables":
        pickle.dump(run_printables(log), open(WORK / "stage_printables.pkl", "wb"))
    elif stage == "report":
        from .report import write_all
        sp = pickle.load(open(WORK / "stage_specs.pkl", "rb"))
        lugs = [pickle.load(open(WORK / f"lug_{s.name}_{v}.pkl", "rb")) for s in sp["specs"] for v in VARIANTS
                if (WORK / f"lug_{s.name}_{v}.pkl").exists()]
        plates = run_plate()
        res = {"frame": run_all(log=None), "specs": sp["specs"], "lugs": lugs, "plates": plates,
               "layout": pickle.load(open(WORK / "stage_layout.pkl", "rb")),
               "printables": pickle.load(open(WORK / "stage_printables.pkl", "rb"))}
        if (WORK / "stage_plate_v2.pkl").exists():
            res["plate_v2"] = pickle.load(open(WORK / "stage_plate_v2.pkl", "rb"))
        write_all(res, log)


def run(iters=36, procs=3, quick=False, log=print):
    import trimesh
    from . import render
    from .loads import run_all
    from .lugs import VARIANTS, build_specs
    for d in (PRINT, ANALYSIS, SCREENS, WORK):
        d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    frame = run_all(log=log)
    specs = build_specs(frame)
    log(f"lug specs: {[s.name for s in specs]} ({time.time() - t0:.0f} s)")
    tasks = [(s, v, frame["fatigue_g"], iters) for s in specs for v in VARIANTS]
    tasks.sort(key=lambda a: -a[0].sockets.__len__())
    ctx = get_context("fork")
    pool = ctx.Pool(procs)
    async_res = pool.map_async(lug_task, tasks, chunksize=1)
    plates = run_plate(log)
    layout = run_layout(frame, log, quick=quick)
    printables = run_printables(log)
    lugs = async_res.get()
    pool.close(); pool.join()
    log(f"all studies done ({time.time() - t0:.0f} s)")
    results = {"frame": frame, "specs": specs, "lugs": lugs, "plates": plates, "layout": layout,
               "printables": printables}
    pickle.dump({k: v for k, v in results.items() if k not in ("frame",)} | {"standard": frame["standard"],
                "fatigue_g": frame["fatigue_g"]}, open(WORK / "results.pkl", "wb"))
    from .report import write_all
    write_all(results, log)
    return results


def benchmark(log=print):
    from . import render
    from .simp import cantilever3d_problem, mbb_problem, run_simp
    import matplotlib.pyplot as plt
    r2 = run_simp(mbb_problem(120, 40, 0.5, 2.0), iters=120, beta_schedule=(0,))
    r3 = run_simp(cantilever3d_problem(40, 10, 20, 0.12, 1.5), iters=40)
    return r2, r3


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.gendesign.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run"); p.add_argument("--iters", type=int, default=36); p.add_argument("--procs", type=int, default=3)
    p.add_argument("--quick", action="store_true")
    sub.add_parser("report")
    sub.add_parser("benchmark")
    st = sub.add_parser("stage"); st.add_argument("name", choices=["lugs", "plate", "plate_v2", "layout", "printables", "report"])
    st.add_argument("--iters", type=int, default=36); st.add_argument("--procs", type=int, default=3)
    st.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "stage":
        run_stage(a.name, a.iters, a.procs, a.quick)
    elif a.cmd == "run":
        run(a.iters, a.procs, a.quick)
    elif a.cmd == "report":
        from .report import write_all
        from .loads import run_all
        res = pickle.load(open(WORK / "results.pkl", "rb"))
        res["frame"] = run_all(log=None)
        write_all(res)
    else:
        benchmark()


if __name__ == "__main__":
    main()
