"""BL-055 Part B: pass lines for the SECOND US1 strain gauge, on the US1 outer cheek's outboard face at its floor.

h1_rev5.md section 4 (BL-053) moved the US1 governing spot from the arm root to the fairlead's outer cheek ("if a
second gauge is fitted put it on the US1 outer cheek's outboard face at its floor (the governing spot, x 80-88,
z 98-104)") but published pass lines only for the arm-root site. This script reads the model stress at that second
site with BL-053's own print submodel (``huntkit.gendesign.h1_rev5.sub_fea``, called read-only, nothing in huntkit is
changed) on the same load steps and rule as ``h1_rev5.gauge_values``:

* MT-1cr: the governing 3D cradle leg (c3d|b40|dy50|out) at 240 / 480 / 720 N and the factored row;
* T1: the bag-on drape row scaled to 0 / 150 / 300 lb (local pin load only, ASSUMPTION GAUGE-LOCAL);
* pass line = the band extreme (voxels within +/- 1.5 mm of the site) x 1.15, as microstrain on E_xy.

Gauge axis: the in-plane normal stress (frame y = across the cheek, from its floor to its tip, or frame z = along the
pin's height) with the larger magnitude at the MT-1cr factored row; the other is recorded too.
ASSUMPTION G2-AXIS: the cheek bends as a plate cantilevered off the fairlead floor, so the larger in-plane normal stress
on its outboard face is the gauge axis. Settled by: MT-1cr, a 2-element 0/90 rosette, or rotating a single gauge
between the two candidate axes on a second P1 cheek; the axis with the larger reading is the governing one.

    python designs/pack_5200/us1_outer_gauge.py          # writes tests_physical/us1_outer_gauge.json (about 1-3 min)

Units mm, N, MPa. Frame: x lateral (+ = R side), y towards the bag, z up; R station (L mirrors x).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = HERE / "tests_physical" / "us1_outer_gauge.json"
TOL = 1.5          # = h1_rev5.GAUGE_TOL (placement band)
SCATTER = 1.15     # = h1_rev5.gauge_values pass rule (band extreme x 1.15)
Z_SITE = 101.0     # h1_rev5.md section 4: "x 80-88, z 98-104": mid of the stated z band
FLOOR_UP = 2.5     # gauge centre this far above the fairlead floor's bag-face level (1 mm grid + half the 1 mm grid)


def site(p: dict, cen: np.ndarray) -> dict:
    """The outboard face of the outer cheek (the cheek towards the stay, x > pin on R), at the floor, z Z_SITE."""
    g = p["geom"]
    x_face = p["x"] + g.throat / 2.0 + g.cheek                      # 70 + 10 + 8 = 88 on R US1
    y = p["y_floor"] + FLOOR_UP
    near = (np.abs(cen[:, 1] - y) <= 1.0) & (np.abs(cen[:, 2] - Z_SITE) <= 1.0) & (cen[:, 0] <= x_face + 0.6) & \
           (cen[:, 0] >= x_face - 4.0)
    xs = float(cen[near, 0].max()) if near.any() else x_face - 0.5   # the surface voxel layer
    return {"x": round(xs, 2), "y": round(y, 2), "z": Z_SITE, "x_face_design": round(x_face, 2),
            "face": "outboard face of the US1 outer cheek (+x on R, towards the stay), at the fairlead floor",
            "station": "us1"}


def compute(log=print) -> dict:
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign import h1_rev5 as R
    E = BA._paht()["E"]
    m = R._mesh()
    p = R.station("us1")
    L = R.lug_loads_3d("us1")
    rev = json.loads(R.RESULTS.read_text())["gauges"]["tests"]
    gov = rev["MT-1cr|us1"]["row"].split("|", 1)[1]
    cases = {"cradle_gov": "c3d|" + gov, "bagon": "bagon_drape"}
    per = {}
    st = None
    for lab, k in cases.items():
        v = np.asarray(L[k]["vec"], float)
        u = v / np.linalg.norm(v)
        t0 = time.time()
        f = R.sub_fea("us1", {"unit": (1000.0 * u).tolist()}, box=R.BOXES["us1"], mesh=m, field="unit")
        fd = f["loads"]["_field"]
        cen, S = fd["cen"], fd["S"]
        if st is None:
            st = site(p, cen)
        d = np.linalg.norm(cen - np.array([st["x"], st["y"], st["z"]]), axis=1)
        surf = cen[:, 0] >= st["x"] - 0.6
        near = (d <= TOL + 0.5) & surf
        if not near.any():
            near = d <= d.min() + 0.5
        j = int(np.argmin(d))
        comp = {}
        for ax, col in (("y", 1), ("z", 2)):
            s = S[:, col] / 1000.0                                     # MPa per N
            comp[ax] = {"mpa_per_n": float(s[j]), "band_mpa_per_n": [float(s[near].min()), float(s[near].max())]}
        per[lab] = {"load": k, "unit": u.round(4).tolist(), "comp": comp, "n_band": int(near.sum())}
        log(f"  {lab} {k}: {comp} ({time.time() - t0:.0f} s)")
    # gauge axis: larger in-plane normal stress at the MT-1cr factored row (ASSUMPTION G2-AXIS)
    c = per["cradle_gov"]["comp"]
    axis = max(c, key=lambda a: max(abs(c[a]["mpa_per_n"]), *map(abs, c[a]["band_mpa_per_n"])))
    other = "z" if axis == "y" else "y"

    def steps(lab, Fs, basis, ax):
        q = per[lab]["comp"][ax]
        rows = []
        for F in Fs:
            s = q["mpa_per_n"] * F
            lo, hi = q["band_mpa_per_n"][0] * F, q["band_mpa_per_n"][1] * F
            lim = max(abs(s), abs(lo), abs(hi))
            rows.append({"pin_load_n": round(F, 1), "sigma_mpa": round(s, 2), "band_mpa": [round(lo, 2), round(hi, 2)],
                         "microstrain": round(s / E * 1e6, 0),
                         "pass_if_abs_microstrain_at_most": round(lim * SCATTER / E * 1e6, 0)})
        return {"pull_unit_vector_frame_R": per[lab]["unit"], "row": per[lab]["load"], "basis": basis,
                "gauge_axis": f"frame {ax}", "steps": rows}

    mt = [s["pin_load_n"] for s in rev["MT-1cr|us1"]["steps"]]
    t1 = [s["pin_load_n"] for s in rev["T1|us1"]["steps"]]
    out = {"ticket": "BL-055 Part B", "source": "designs/pack_5200/us1_outer_gauge.py (h1_rev5.sub_fea, read-only)",
           "E_xy_mpa": E, "site": st, "gauge_axis": f"frame {axis}", "other_axis": f"frame {other}",
           "assumptions": ["G2-AXIS", "GAUGE-LOCAL (T1)", "SUB-BC (h1_rev5)"],
           "tests": {
               "MT-1cr|us1_outer": steps("cradle_gov", mt, "same steps as MT-1cr|us1 (h1_rev5.json gauges)", axis),
               "T1|us1_outer": steps("bagon", t1, "same steps as T1|us1 (h1_rev5.json gauges); local pin load only",
                                     axis),
               "MT-1cr|us1_outer_other_axis": steps("cradle_gov", mt, "record only: the other in-plane axis", other)}}
    return out


def stl_md5() -> str:
    """md5 of the assembled print the submodel reads (h1_rev5._mesh default)."""
    import hashlib
    return hashlib.md5((ROOT / "designs/pack_5200/print/frame_h1/h1_assembled.stl").read_bytes()).hexdigest()


def republish(res: dict, old: dict | None) -> dict:
    """BL-061: the record locked to the STL md5 it was run on (as gauge_lines_bl060.json), with the lines it replaces."""
    out = {**res, "ticket": "BL-061 (re-run of BL-055 Part B on the current print)", "stl_md5": stl_md5()}
    if old:
        out["was"] = {"ticket": old.get("ticket"), "stl_md5": old.get("stl_md5"),
                      "lines": {k: [s["pass_if_abs_microstrain_at_most"] for s in v["steps"]]
                                for k, v in old.get("tests", {}).items()}}
    return out


def main(argv=None) -> int:
    old = json.loads(OUT.read_text()) if OUT.exists() else None
    res = republish(compute(), old)
    OUT.write_text(json.dumps(res, indent=1, default=float))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
