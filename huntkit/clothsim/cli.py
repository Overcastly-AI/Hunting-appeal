"""CLI for huntkit.clothsim (batch cloth and pack simulator, phase 1).

  python -m huntkit.clothsim.cli validate [--screens outputs/screens] [--date 20261105]
  python -m huntkit.clothsim.cli run [--scenario FILE] [--cases empty,packed,fill,meat] [--fine]
                                     [--time-cap 900] [--out outputs/clothsim/<name>] [--no-render] [--no-sweep]
  python -m huntkit.clothsim.cli diff BEFORE/results.json AFTER/results.json [--out diff.md]

``run`` writes results.json (every number in the report), x_<case>.npy (deformed nodes),
clothsim_<case>.glb + an offline viewer HTML (huntkit.viz3d viewer, strain colour map) and PNGs.
"Adjusting a panel" = a scenario YAML with a changed ``panels:`` entry (see
huntkit/clothsim/scenarios/pack5200_v31.yaml), ``run`` it, then ``diff`` the two results.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import numpy as np

from .pack import REPO, SCENARIO, PackModel, load_scenario, run_case
from .report import (diff_tables, export_viewer, plot_profiles, plot_seams, plot_strain_views, plot_validation,
                     render_viewer, summarize, to_json)


def _screens(a):
    d = Path(a.screens)
    d.mkdir(parents=True, exist_ok=True)
    return d, a.date or dt.date.today().strftime("%Y%m%d")


def cmd_validate(a) -> dict:
    from . import validation as V
    t = time.time()
    cyl = V.cylinder()
    cat = V.catenary()
    dr = V.drape_area()
    from .assemble import densify
    from .mesh import triangulate_loop
    loop = np.array([[0, 0], [300, 0], [300, 250], [170, 250], [150, 140], [130, 250], [0, 250]], float)
    tr = triangulate_loop(densify(np.vstack([loop, loop[:1]]), 15.0)[:-1], 20.0)
    A = tr["xy"][tr["tris"]]
    ar = 0.5 * np.abs((A[:, 1, 0] - A[:, 0, 0]) * (A[:, 2, 1] - A[:, 0, 1]) - (A[:, 1, 1] - A[:, 0, 1]) * (A[:, 2, 0] - A[:, 0, 0]))
    val = {"cylinder": {k: v for k, v in cyl.items() if k not in ("mesh", "x", "info")},
           "catenary": {k: v for k, v in cat.items() if k not in ("mesh", "x", "info")},
           "area": {"drape_ratio": dr["area_3d"] / dr["flat_area"], "mesher_ratio": float(ar.sum() / tr["polygon"].area),
                    "drape_sag_mm": dr["sag"]}}
    bag = Path(a.bag_results) if getattr(a, "bag_results", None) else None
    if bag and bag.exists():
        r = json.loads(bag.read_text())
        val["area"]["bag_ratio"] = r["cases"]["meat"]["area"]["ratio"]
    val["errors_pct"] = {"hoop": (cyl["hoop"] / cyl["hoop_exact"] - 1) * 100,
                         "axial": (cyl["axial"] / cyl["axial_exact"] - 1) * 100,
                         "seam_longitudinal": (cyl["seam_long"] / cyl["hoop_exact"] - 1) * 100,
                         "seam_cap": (cyl["seam_cap"] / cyl["axial_exact"] - 1) * 100,
                         "radius": (cyl["r_eq"] / cyl["r_exact_linear"] - 1) * 100,
                         "catenary_sag": (cat["sag"] / cat["sag_exact"] - 1) * 100,
                         "catenary_H": (cat["H"] / cat["H_exact"] - 1) * 100,
                         "catenary_V": (cat["V"] / cat["V_exact"] - 1) * 100,
                         "drape_area": (val["area"]["drape_ratio"] - 1) * 100,
                         "mesher_area": (val["area"]["mesher_ratio"] - 1) * 100}
    val["catenary"]["shape_err_mm"] = cat["shape_err_mm"]
    val["seconds"] = time.time() - t
    out = Path(a.out or REPO / "outputs" / "clothsim")
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation.json").write_text(json.dumps(to_json(val), indent=1, default=float))
    d, date = _screens(a)
    png = d / f"{date}_clothsim_1.png"
    plot_validation(val, png)
    for k, v in val["errors_pct"].items():
        print(f"  {k:20s} {v:+7.3f} %")
    print(f"validation.json -> {out / 'validation.json'}\nPNG  {png}")
    return val


def cmd_run(a) -> dict:
    scen = load_scenario(a.scenario)
    if a.time_cap:
        scen["solver"]["time_cap_s"] = float(a.time_cap)
    name = scen.get("name", Path(a.scenario or SCENARIO).stem)
    out = Path(a.out or REPO / "outputs" / "clothsim" / name)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    pm = PackModel(scen, fine=a.fine)
    m = pm.mesh
    print(f"[{name}] sewn bag: {m.n} nodes, {len(m.tris)} triangles (h {pm.h:.0f} mm), "
          f"{len([k for k in pm.seams if not k.startswith('_')])} seam segments groups, "
          f"{len(pm.diag['free_segments'])} open boundary segments, {time.time() - t0:.1f} s")
    cases = a.cases.split(",") if a.cases else list(scen["cases"])
    if any(scen["cases"][c].get("contents_L") == "auto" for c in cases) and "packed" not in cases:
        cases = ["packed"] + cases
    res, xs, sims = {}, {}, {}
    Vpack = None
    for c in cases:
        case = dict(scen["cases"][c])
        if case.get("contents_L") == "auto":
            case["contents_L"] = Vpack
        t = time.time()
        x, sim, infos = run_case(pm, case, verbose=a.verbose)
        r = summarize(pm, c, case, x, sim, infos)
        if c == "packed":
            Vpack = r["volume"]["closed_L"]
        res[c], xs[c], sims[c] = r, x, sim
        np.save(out / f"x_{c}.npy", x)
        sc = r["seam_critical"]
        print(f"  {c:7s} {'converged' if r['converged'] else 'NOT converged'} ({time.time() - t:.0f} s): "
              f"V {r['volume']['closed_L']:.1f} L (body {r['volume']['body_below_collar_seam_L']:.1f}), "
              f"max strain {max(p['e_max_pct'] for p in r['pieces'].values()):.2f} %, "
              f"critical seam {sc['seam']} {sc['max_n_mm']:.2f} N/mm SF {sc['sf']:.0f}")
    sweep = []
    if not a.no_sweep:
        xprev = None
        for p in scen.get("volume_sweep_kpa", []):
            case = {"p0_kpa": p, "wraps": False}
            x, sim, infos = run_case(pm, case, x0=xprev)
            xprev = x
            r = summarize(pm, f"sweep_{p}", case, x, sim, infos)
            sweep.append({"p0_kpa": p, "closed_L": r["volume"]["closed_L"],
                          "body_L": r["volume"]["body_below_collar_seam_L"], "converged": r["converged"],
                          "e_p99_max_pct": max(v["e_p99_pct"] for v in r["pieces"].values())})
            print(f"  sweep {p:.2f} kPa: V {sweep[-1]['closed_L']:.2f} L, body {sweep[-1]['body_L']:.2f} L")
    summary = {"scenario": name, "scenario_file": str(a.scenario or SCENARIO), "date": dt.date.today().isoformat(),
               "mesh": {"nodes": m.n, "triangles": len(m.tris), "h_mm": pm.h,
                        "open_boundary_segments": len(pm.diag["free_segments"]),
                        "pieces": [p.name for p in m.pieces]},
               "cases": res, "volume_sweep": sweep, "seconds": time.time() - t0,
               "source": {"patterns": "designs/pack_5200/patterns_v31.py build_body (= outputs/release/pack5200_v3.1_patterns)",
                          "frame": "designs/pack_5200/print/frame/genframe_assembled.stl",
                          "spreader": "designs/pack_5200/print/frame/genframe_barrier.stl"}}
    (out / "results.json").write_text(json.dumps(to_json(summary), indent=1, default=float))
    print(f"results.json -> {out / 'results.json'}")
    if not a.no_render:
        d, date = _screens(a)
        files = []
        main = "meat" if "meat" in res else cases[-1]
        f = d / f"{date}_clothsim_3.png"
        plot_strain_views(pm, res[main], xs[main], f,
                          f"{name}: sewn bag under '{main}', max principal strain (frame grey)")
        files.append(f)
        f = d / f"{date}_clothsim_4.png"
        plot_seams({c: res[c] for c in res if c != "packed"}, f)
        files.append(f)
        f = d / f"{date}_clothsim_5.png"
        plot_profiles(pm, {c: xs[c] for c in xs if c != "packed"}, sweep, f)
        files.append(f)
        for c in [k for k in ("meat", "fill") if k in res]:
            v = export_viewer(pm, res[c], xs[c], sims[c], out, c,
                              f"{name}: '{c}' case, strain colour map, frame + spreader + straps")
            print(f"GLB  {v['glb']}\nHTML {v['html']}")
            if c == main:
                try:
                    shots = [{"file": str((d / f"{date}_clothsim_2.png").resolve()), "view": "hero",
                              "state": {"mode": "pack"}, "caption": f"Sewn bag, {c} case: strain 0-{v['vmax']:.1f} % (turbo)",
                              "sub": "30 kg meat on IM1-IM3 + 38 kg gear, HA-LS-1 C1 static carry"},
                             {"file": str((d / f"{date}_clothsim_6.png").resolve()), "view": "side",
                              "state": {"mode": "pack"}, "caption": f"Side profile, {c} case",
                              "sub": "bag on the spreader and frame, straps in tan"}]
                    files += render_viewer(v["html"], shots)
                except Exception as e:  # noqa: BLE001
                    print("viewer render skipped:", e)
        print("SCREENSHOTS:")
        for f in files:
            print(f"  {f}  ({f.stat().st_size / 1e6:.2f} MB)")
    return summary


def cmd_diff(a):
    A = json.loads(Path(a.before).read_text())
    B = json.loads(Path(a.after).read_text())
    md = diff_tables(A, B)
    if a.png:
        from .report import plot_diff
        plot_diff(A, B, Path(a.png), a.case)
        print(f"PNG  {a.png}")
    if a.out:
        Path(a.out).write_text(md)
        print(f"diff -> {a.out}")
    print(md)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.clothsim.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="analytic validation cases + PNG")
    v.add_argument("--out", default=None)
    v.add_argument("--screens", default=str(REPO / "outputs" / "screens"))
    v.add_argument("--date", default=None)
    v.add_argument("--bag-results", default=None, help="results.json of a bag run (adds its area ratio to the plot)")
    r = sub.add_parser("run", help="sew the v3.1 bag, run the load cases, write results/GLB/PNGs")
    r.add_argument("--scenario", default=None)
    r.add_argument("--cases", default=None, help="comma list (default: all in the scenario)")
    r.add_argument("--fine", action="store_true", help="fine mesh (scenario mesh.fine_h)")
    r.add_argument("--time-cap", type=float, default=None, help="seconds per load case")
    r.add_argument("--out", default=None)
    r.add_argument("--screens", default=str(REPO / "outputs" / "screens"))
    r.add_argument("--date", default=None)
    r.add_argument("--no-render", action="store_true")
    r.add_argument("--no-sweep", action="store_true")
    r.add_argument("--verbose", action="store_true")
    d = sub.add_parser("diff", help="before/after Markdown table of two results.json")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--out", default=None)
    d.add_argument("--png", default=None, help="before/after bar chart PNG")
    d.add_argument("--case", default="meat")
    a = ap.parse_args(argv)
    {"validate": cmd_validate, "run": cmd_run, "diff": cmd_diff}[a.cmd](a)


if __name__ == "__main__":
    main()
