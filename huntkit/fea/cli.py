"""CLI for huntkit.fea.

  python -m huntkit.fea.cli demo [--out outputs/fea_demo]
  python -m huntkit.fea.cli solve model.yaml [--out DIR] [--buckling]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .analysis import run_study, summarize
from .frames import aluminum_baseline, carbon_variant
from .report import report


def demo(out: str = "outputs/fea_demo", torsos=(15, 19, 23)) -> Path:
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    studies = []
    for name, builder in (("CFRP", carbon_variant), ("Al 7075", aluminum_baseline)):
        for t in torsos:
            fm = builder(torso_in=t)
            studies.append(run_study(fm, label=f"{name} {t:g} in torso"))
        fm = builder(torso_in=19, haul_mode=True)
        studies.append(run_study(fm, label=f"{name} 19 in, frame-only haul"))
    md = report(studies, outdir / "report.md",
                title="Placeholder pack frame - FEA demo (carbon primary, aluminium baseline)")
    with open(md, "a") as f:
        f.write("\n".join(plate_example(studies[1])) + "\n")
    with open(outdir / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config", "case", "min_sf", "required_sf", "critical", "buckling",
                    "joint_sf_avg", "joint_sf_peak", "pass", "tube_mass_g"])
        for s in studies:
            mass = next(iter(s["results"].values())).mass_kg * 1e3
            for r in summarize(s):
                w.writerow([s["label"], r["case"], f"{r['min_sf']:.3f}", r["required_sf"], r["critical"],
                            f"{r['buckling']:.2f}", f"{r['joint_sf']:.3f}", f"{r['joint_peak_sf']:.3f}",
                            r["pass"], f"{mass:.1f}"])
    return md


def plate_example(study) -> list[str]:
    """Illustrative Kirchhoff-plate check: CFRP lumbar plate bridging the stays, loaded by the
    lumbar-pad bearing reaction of the tall_load case."""
    from .materials_bridge import get_material
    from .plate import kirchhoff_plate
    r = study["results"]["tall_load"]
    hip = study["frame"]["groups"]["hipbelt"]
    Fy = abs(sum(r.reactions[n][1] for n in hip))
    mat = get_material("cfrp_plate_quasi_iso")
    p = study["frame"]["params"]
    a = p["width_bottom"] - 12.7          # clear span between stay tubes (approx.)
    b, t = 100.0, 1.5
    q = Fy / (a * b)
    pr = kirchhoff_plate(a, b, t, E=mat.require("youngs_modulus_mpa"), nu=mat.get("poisson", 0.3), q=q,
                         edges={"left": "ss", "right": "ss", "bottom": "free", "top": "free"})
    allow = float(mat.get("compressive_strength_mpa", 450)) * 0.8 * 0.65
    return ["## Plate check example: CFRP lumbar plate between the stays", "",
            f"Quasi-isotropic CFRP plate ({mat.id}, source {mat.source}) {a:.0f} x {b:g} x {t:g} mm, simply "
            f"supported on the two stays, free top/bottom edges, uniform pressure {q * 1e3:.1f} kPa = the "
            f"lumbar bearing reaction {Fy:.0f} N of `tall_load` ({study['label']}). Kirchhoff/Morley plate "
            f"(`huntkit.fea.plate`, verified vs Navier).", "",
            f"- max deflection {pr.w_max:.1f} mm; peak bending stress {pr.sigma_vm_max:.0f} MPa; allowable "
            f"{allow:.0f} MPa (compression strength x0.8 hot/wet x0.65 impact) -> SF {allow / pr.sigma_vm_max:.2f}",
            "- ASSUMPTION: homogenised quasi-isotropic plate, uniform pad pressure; do a ply-level check with "
            "`composite.Laminate` once the layup is chosen. Linear theory: deflection > ~t/2 means membrane "
            "action, so treat the numbers as indicative.", ""]


def solve_file(path: str, out: str | None, buckling: bool):
    import yaml
    from .frame import solve
    model = yaml.safe_load(Path(path).read_text())
    res = solve(model, buckling=buckling, name=Path(path).stem)
    print(f"min SF {res.min_sf:.3f} at {res.critical_member['id']}; buckling {res.buckling_sf:.2f}; "
          f"max disp {res.max_displacement():.3f} mm; mass {res.mass_kg * 1e3:.1f} g")
    if out:
        print(report(res, out))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.fea.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="placeholder pack frame, all load cases, writes a report")
    d.add_argument("--out", default="outputs/fea_demo")
    s = sub.add_parser("solve", help="solve a YAML frame model")
    s.add_argument("model")
    s.add_argument("--out")
    s.add_argument("--buckling", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        print(demo(a.out))
    else:
        solve_file(a.model, a.out, a.buckling)


if __name__ == "__main__":
    main()
