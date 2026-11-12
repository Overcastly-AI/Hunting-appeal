"""Re-evaluate the reported contact forces of stored cloth-sim runs on the right gap field (BL-025).

Until BL-025, :func:`huntkit.clothsim.pack.run_case` restored x to the last converged contact-rounding stage when a
stage failed, but left the contact terms on the field of the failed stage. ``report.summarize`` then evaluated the
``contact_*`` forces (and the spreader footprint) on that sharper field. Everything else in a results.json (strap,
hook, hinge and seam forces, volume, CG, profile) depends on x only and is unaffected.

The contact force of a stored state needs only the node positions ``x_<case>.npy``, the scenario's ``contact`` block
(kc, clearance, field settings, crown) and the frame / spreader gap fields, which do not depend on the bag: no
pattern or mesh rebuild is needed. For each case this module evaluates

* ``reported``: the field the buggy report used (the last stage TRIED, parsed from the solve log), as a check that
  the stored number is reproduced, and
* ``kept``: the field of the kept stage (``contact_rounding_mm``), i.e. the corrected value.

CLI::

    python -m huntkit.clothsim.recontact outputs/clothsim/corrie_f/F_r1_PR15_fineFM [more run dirs] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

from .model import FieldContact
from .pack import REPO, crown_field, frame_clouds, gap_fields, load_scenario

_FIELDS: dict = {}


def _raw_fields(cs: dict) -> dict:
    """Unsmoothed spreader / frame (/ crown) gap fields for a scenario contact block (as PackModel.fields_raw)."""
    key = json.dumps({k: v for k, v in cs.items() if k not in ("smooth_mm", "smooth_continuation", "kc", "clearance")},
                     sort_keys=True, default=str)
    if key not in _FIELDS:
        f = dict(gap_fields(frame_clouds(float(cs.get("spacing", 4.0))), cs))
        if (cs.get("crown") or {}).get("enabled"):
            f["crown"] = crown_field(cs["crown"], cs)
        _FIELDS[key] = {"raw": f, "smooth": {}}
    return _FIELDS[key]


def field_at(cs: dict, name: str, sigma: float):
    """Gap field ``name`` at contact rounding ``sigma`` mm (0 = raw), cached."""
    d = _raw_fields(cs)
    if name not in d["raw"]:
        return None
    if sigma <= 0:
        return d["raw"][name]
    k = (name, round(float(sigma), 3))
    if k not in d["smooth"]:
        d["smooth"][k] = d["raw"][name].smoothed(float(sigma))
    return d["smooth"][k]


def contact_forces(x: np.ndarray, cs: dict, sigma: float) -> dict:
    """{contact_<name>: {"nodes", "force_n", "force_total_n"}} on the field at ``sigma`` (report.summarize rule)."""
    out = {}
    for nm in ("spreader", "frame", "crown"):
        f = field_at(cs, nm, sigma)
        if f is None:
            continue
        idx, fb = FieldContact(f, kc=cs["kc"], clearance=cs["clearance"]).forces(x)
        F = fb.sum(0) if len(idx) else np.zeros(3)
        out[f"contact_{nm}"] = {"nodes": int(len(idx)), "force_n": [round(float(v), 1) for v in F],
                                "force_total_n": round(float(np.linalg.norm(F)), 1)}
    return out


def pass_through(x: np.ndarray, cs: dict, margin_mm: float = 25.0) -> dict:
    """Bag nodes that have tunnelled through the spreader (penalty contact pass-through). The spreader's bag-facing
    skin (samples with n_y > spreader_ny_min, as the gap field) gives a face height y(x, z); a node inside the face's
    x-z outline and more than ``margin_mm`` behind it (toward the wearer) is through. A sound state has none. 25 mm is
    above the local rim penetration seen on sound coarse runs (up to 16 mm at a 6 mm rounding, F_r1_PR15 meat) and
    well below a tunnelled panel (61 nodes up to 70 mm, F_r1_PR15_goff_sm8 meat)."""
    from scipy.spatial import cKDTree
    cl = frame_clouds(float(cs.get("spacing", 4.0)))
    sel = cl["spreader_n"][:, 1] > float(cs.get("spreader_ny_min", 0.5))
    P = cl["spreader_p"][sel]
    lo, hi = P[:, [0, 2]].min(0), P[:, [0, 2]].max(0)
    inw = np.all((x[:, [0, 2]] > lo) & (x[:, [0, 2]] < hi), axis=1)
    if not inw.any():
        return {"nodes_in_window": 0, "nodes_through": 0, "deepest_mm": 0.0}
    d, j = cKDTree(P[:, [0, 2]]).query(x[inw][:, [0, 2]])
    behind = P[j, 1] - x[inw, 1]
    near = d < 15.0                 # over the face itself, not beside its rim
    thr = near & (behind > margin_mm)
    return {"nodes_in_window": int(near.sum()), "nodes_through": int(thr.sum()),
            "deepest_mm": round(float(behind[near].max()) if near.any() else 0.0, 1)}


_STAGE = re.compile(r"^contact rounding ([0-9.]+) mm:")


def stages(case: dict, cs: dict) -> dict:
    """Rounding of the kept stage and of the field the old report used (the last stage tried), mm."""
    tried = [float(m.group(1)) for s in case.get("solve", []) if (m := _STAGE.match(str(s.get("stage", ""))))]
    start = float(cs.get("smooth_mm", 0.0) or 0.0)
    kept = case.get("contact_rounding_mm")
    stopped = any("kept the last converged stage" in str(s.get("stage", "")) for s in case.get("solve", []))
    return {"kept": None if kept is None else float(kept), "used_by_report": tried[-1] if tried else start,
            "start": start, "stopped": stopped}


def recontact_run(run_dir) -> dict:
    """Corrected contact forces for every case of one run directory (results.json + x_<case>.npy)."""
    rd = Path(run_dir)
    rj = json.loads((rd / "results.json").read_text())
    scen = load_scenario(rj["scenario_file"])
    cs = scen["contact"]
    out = {"run": str(rd.relative_to(REPO)) if rd.is_absolute() and REPO in rd.parents else str(rd),
           "scenario_file": rj["scenario_file"], "cases": {}}
    for cn, c in rj["cases"].items():
        xf = rd / f"x_{cn}.npy"
        if not xf.exists() or "contact" not in c:
            continue
        x = np.load(xf)
        st = stages(c, cs)
        rep = {k: v["force_total_n"] for k, v in c["contact"].items() if k.startswith("contact_")}
        row = {"stages": st, "stored": rep}
        if st["kept"] is None:          # the first solve did not converge: no continuation ran, fields were never moved
            row["kept"] = rep
            row["reproduced_n"] = None
        else:
            used = contact_forces(x, cs, st["used_by_report"])
            kept = contact_forces(x, cs, st["kept"]) if st["kept"] != st["used_by_report"] else used
            row["reproduced_n"] = {k: v["force_total_n"] for k, v in used.items()}
            row["kept"] = {k: v["force_total_n"] for k, v in kept.items()}
            row["kept_detail"] = kept
        row["pass_through"] = pass_through(x, cs)
        row["change_pct"] = {k: (round(100.0 * (row["kept"][k] - v) / v, 1) if v and v > 1e-6 else None)
                             for k, v in rep.items() if k in row["kept"]}
        out["cases"][cn] = row
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.clothsim.recontact", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    res = []
    for r in a.runs:
        try:
            o = recontact_run(r)
        except Exception as e:  # noqa: BLE001
            print(f"{r}: skipped ({e})")
            continue
        res.append(o)
        for cn, c in o["cases"].items():
            print(f"{o['run']:55s} {cn:7s} kept {c['stages']['kept']} used {c['stages']['used_by_report']}  "
                  + "  ".join(f"{k[8:]} {c['stored'][k]:.1f}->{c['kept'][k]:.1f} ({c['change_pct'][k]})"
                              for k in c["stored"] if k in c["kept"]))
            if c["pass_through"]["nodes_through"]:
                print(f"{'':55s} {'':7s} PASS-THROUGH: {c['pass_through']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
