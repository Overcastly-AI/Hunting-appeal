"""BL-056 (orchestrator addition 1): the US2 clevis joint strengthened for the CLEVIS-SHARE B bound (share 1.0).

At outer-cheek share 1.0 the BL-053 joint read fatigue 0.86 on the BL-051 lane row with the 50 mm belly (net section
of the body block through the nut traps, h1_bedfit.joint_check), and 1.14 on the worst 3D cradle row: the
CLEVIS-SHARE B test was predicted to fail. Fix: the joint blocks (body and clevis) grow UPWARD only, from pin + 14.5
to pin + 19 (``h1_bedfit.BLOCK_UP_Z``); the lower edge, the r 3 lip the US2 strap wraps, the bolts (z pin +/- 7),
the hex traps and the head counterbores are unchanged.

This module re-checks on the re-exported print: the joint at share 0.6 and 1.0 (every row), trap walls, the joint
slices, the bed fit of both halves, the clevis pieces, the strap wrap and the strap clearance (us_route, >= 10 mm),
the counterbored heads against the drapes (us_route.head_clearance), the CLEVIS-SHARE A / B and MT-1cr US2 gauge
lines on the new print (h1_rev5.gauge_values), and the mass against the BL-055 print.

CLI: ``python -m huntkit.gendesign.clevis_bl056`` writes ``analysis/clevis_bl056.json`` (caches in outputs/bl056).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
PRINT = PACK / "print" / "frame_h1"
OUT = ROOT / "outputs" / "bl056"
BEFORE = OUT / "before"            # the BL-055 print files, copied before the re-export
DATE = "2026-11-21"
FAT_GOAL, SF_GOAL = 1.15, 1.5


def _cached(name: str, fn):
    p = OUT / name
    if not p.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(fn(), indent=1, default=float))
    return json.loads(p.read_text())


def joint_rows(wrap: dict) -> dict:
    """h1_rev5.joint on the BL-056 blocks, plus the per-share minimum over EVERY row (design rows and the BL-051 lane
    rows kept for comparison)."""
    from . import h1_bedfit as BF
    from . import h1_rev5 as R
    j = R.joint(wrap)
    L = {k: {kk: v[kk] for kk in ("vec", "g_times_req")} for k, v in R.lug_loads_3d("us2").items()}
    for sh in (BF.CHEEK_SHARE, 1.0):
        jc = BF.joint_check(share=sh, loads={**L, **j["wrap_rows"]})
        j[f"share_{sh:g}"]["all_rows_min"] = {"strength": min(r["min_sf"] for r in jc["rows"].values()),
                                             "fatigue": min(r["min_fatigue"] for r in jc["rows"].values())}
        j[f"share_{sh:g}"]["net_section_rows_min"] = {
            "strength": min(r["sf"]["net_section"] for r in jc["rows"].values()),
            "fatigue": min(r["fatigue"]["net_section_paht"] for r in jc["rows"].values())}
    j["block"] = {"lower_half_z_mm": BF.BLOCK_HALF_Z, "upper_half_z_mm": BF.BLOCK_UP_Z, "was_upper_mm": 14.5,
                  "nut_face_x_mm": BF.JOINT.nut_face, "was_nut_face_x_mm": 151.0, "body_plug_mm": BF.JOINT.L_body,
                  "trap_x0_mm": BF.JOINT.trap_x0}
    # the legacy BL-050 / BL-051 row set (h1_lanes.lug_loads, incl. the 2D 'cradle' rows) at share 1.0 as well
    lg = BF.joint_check(share=1.0)
    j["legacy_rows_share_1"] = {"strength": min(r["min_sf"] for r in lg["rows"].values()),
                                "fatigue": min(r["min_fatigue"] for r in lg["rows"].values()),
                                "worst_fatigue": lg["worst_fatigue"]}
    return j


def kit_loads(joint: dict, gauges: dict) -> dict:
    """CLEVIS-SHARE A / B as the kit needs them: pull direction, proof and cycle loads, where the eye bears, the force
    on the clevis at the bound share and the model margin there, the gauge lines."""
    from . import h1_rev5 as R
    L = R.lug_loads_3d("us2")
    out = {}
    for key, lab, row, share in (("A", "CLEVIS-SHARE|us2_inboard", None, 0.6),
                                 ("B", "CLEVIS-SHARE|us2_yz", "c3d|b40|dy95|out", 1.0)):
        t = gauges["tests"][lab]
        F = t["steps"][0]["pin_load_n"]
        u = t["pull_unit_vector_frame_R"]
        out[key] = {"test": lab, "row": t["row"], "pull_unit_vector_frame_R": u, "mirror_for_L": "negate x",
                    "proof_n": F, "proof_lbf": round(F / 4.448, 0), "cycle_peak_n": t["steps"][1]["pin_load_n"],
                    "cycles": 100000, "R": 0.1, "eye_bears_on": t.get("eye_bears_on"),
                    "share_on_clevis": share,
                    "model_min_strength_at_share": joint[f"share_{share:g}"]["all_rows_min"]["strength"],
                    "model_min_fatigue_at_share": joint[f"share_{share:g}"]["all_rows_min"]["fatigue"],
                    "gauge_lines": t["steps"],
                    "pass": "every step |microstrain| <= the line; after the proof (60 s hold) and after the 1e5 "
                            "cycles: torque marks on the 2 clevis bolts unmoved, no whitening / crack at the traps "
                            "or the counterbores under a 10x loupe, joint face gap < 0.1 mm (feeler)"}
    return out


def clearance() -> dict:
    """us_route's strap clearance on the re-exported print (as outputs/h1_rev5/clear.py ran it for BL-053)."""
    import trimesh
    from . import h1_rev5 as R
    U = R._U()
    F = U._F()
    mesh = trimesh.load(U.PRINT)
    T = U.tensions()
    dr = {t: F.drape(U.RUN.format(t=t), U.CASE) for t in U.TORSOS}
    r = U.run_layout("now", mesh, dr, T)
    return {"worst_clear_mm": r["worst_clear_mm"], "pass": r["pass"],
            "rows": [{k: q[k] for k in ("torso", "side", "strap", "clear_mm", "min_clear_mm", "pass")}
                     for q in r["rows"]]}


def heads() -> dict:
    from . import h1_rev5 as R
    return R._U().head_clearance()


def masses() -> dict:
    import trimesh
    rho = 1.06e-3                   # PAHT-CF g/mm3 as the export books it (h1_closeout.stl_check 1.06e-3)
    out = {}
    for f in ("h1_assembled", "h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R"):
        a = trimesh.load(PRINT / f"{f}.stl", force="mesh")
        b = trimesh.load(BEFORE / f"{f}.stl", force="mesh")
        out[f] = {"g": round(a.volume * rho, 2), "bl055_g": round(b.volume * rho, 2),
                  "delta_g": round((a.volume - b.volume) * rho, 2), "watertight": bool(a.is_watertight),
                  "shells": len(a.split(only_watertight=False))}
    # the assembled print holds the clevises: its delta is the whole BL-056 print change
    out["print_delta_g"] = out["h1_assembled"]["delta_g"]
    return out


def gauges() -> dict:
    from . import h1_rev5 as R
    g = R.gauge_values(log=None)
    keep = {k: v for k, v in g["tests"].items() if k.startswith(("CLEVIS-SHARE", "MT-1cr|us2"))}
    return {"E_xy_mpa": g["E_xy_mpa"], "site_us2": g["sites"]["us2"], "tests": keep}


def gauges_bl053() -> dict:
    p = ANALYSIS / "h1_rev5.json"
    g = json.loads(p.read_text())["gauges"]
    return {k: v for k, v in g["tests"].items() if k.startswith(("CLEVIS-SHARE", "MT-1cr|us2"))}


def compute() -> dict:
    import trimesh
    from . import h1_bedfit as BF
    from . import h1_rev5 as R
    res = {"ticket": "BL-056 (addition 1: US2 clevis)", "date": DATE}
    m = trimesh.load(PRINT / "h1_assembled.stl", force="mesh")
    res["strap_wrap"] = _cached("wrap.json", lambda: R._U().strap_wrap(m))
    res["joint"] = _cached("joint.json", lambda: joint_rows(res["strap_wrap"]))
    s1 = res["joint"]["share_1"]
    res["share_1_pass"] = bool(s1["all_rows_min"]["fatigue"] >= FAT_GOAL and s1["all_rows_min"]["strength"] >= SF_GOAL)
    res["trap_walls"] = BF.trap_walls()
    res["slices"] = BF.joint_slices()
    res["bed"] = {nm: BF.bed_check(PRINT / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    res["clearance"] = _cached("clearance.json", clearance)
    try:
        res["heads"] = _cached("heads.json", heads)
    except Exception as e:          # pragma: no cover  (drape files missing in a fresh checkout)
        res["heads"] = {"error": str(e)}
    res["gauges"] = _cached("gauges.json", gauges)
    res["gauges_bl053"] = gauges_bl053()
    res["kit"] = kit_loads(res["joint"], res["gauges"])
    res["mass"] = masses()
    res["assumptions"] = [
        {"id": "CLEVIS-SHARE", "text": "Carried (BL-053): outer-cheek share 0.6, 1.0 as the bound; BL-056 makes the "
         "bound pass on every row.", "settled_by": "CLEVIS-SHARE A and B (gauge lines here)."},
        {"id": "BLOCK-UP", "text": "Growing the blocks upward adds no new strap contact: the strap wraps the lower lip "
         "only (strap_wrap re-run on the new print).", "settled_by": "FIT-US on the re-printed us_route_stay_R piece."},
    ]
    return res


def main(argv=None):  # pragma: no cover
    res = compute()
    (ANALYSIS / "clevis_bl056.json").write_text(json.dumps(res, indent=1, default=float))
    s1 = res["joint"]["share_1"]
    print(json.dumps({"share_1": s1["all_rows_min"], "share_0.6": res["joint"]["share_0.6"]["all_rows_min"],
                      "clear": res["clearance"]["worst_clear_mm"], "mass": res["mass"]["print_delta_g"],
                      "bed": {k: v.get("fits_with_brim", v) for k, v in res["bed"].items()}}, indent=1, default=float))


if __name__ == "__main__":  # pragma: no cover
    main()


def plot_joint(res: dict) -> str:
    """Sections of the R US2 joint through the body block's trap plane and through the clevis (|x| 170), BL-055 print
    (grey) against BL-056 (blue), with the share-1.0 SF bars per check family."""
    import matplotlib.pyplot as plt
    import numpy as np
    import trimesh
    from . import h1_bedfit as BF
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6))
    for ax, xs, ttl in ((axs[0], 0.5 * (BF.JOINT.trap_x0 + BF.JOINT.nut_face), "body block, trap plane"),
                        (axs[1], 170.0, "clevis, |x| 170")):
        for path, col, lab in ((BEFORE / "h1_assembled.stl", "#999", "BL-055"),
                               (PRINT / "h1_assembled.stl", "#1f6fb4", "BL-056")):
            m = trimesh.load(path, force="mesh")
            s = m.section(plane_origin=[xs, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
            first = True
            for L in s.discrete:
                L = np.asarray(L)
                if np.all(np.abs(L[:, 2] - p["z"]) < 40) and np.all(np.abs(L[:, 1] - p["yc"]) < 40):
                    ax.plot(L[:, 1], L[:, 2], color=col, lw=1.2 if col != "#999" else 2.2,
                            label=lab if first else None)
                    first = False
        ax.axhline(p["z"], color="k", lw=0.5, ls=":")
        ax.set_aspect("equal"); ax.set_xlabel("frame y"); ax.set_ylabel("frame z")
        ax.set_title(f"{ttl}: block z pin -{BF.BLOCK_HALF_Z:g} / +{BF.BLOCK_UP_Z:g}", fontsize=9)
        ax.legend(fontsize=7, loc="lower right")
    j = res["joint"]
    labs = ["share 0.6 strength", "share 0.6 fatigue", "share 1.0 strength", "share 1.0 fatigue"]
    new = [j["share_0.6"]["all_rows_min"]["strength"] / SF_GOAL, j["share_0.6"]["all_rows_min"]["fatigue"] / FAT_GOAL,
           j["share_1"]["all_rows_min"]["strength"] / SF_GOAL, j["share_1"]["all_rows_min"]["fatigue"] / FAT_GOAL]
    old = [3.17 / SF_GOAL, 1.43 / FAT_GOAL, 1.90 / SF_GOAL, 0.86 / FAT_GOAL]     # h1_rev5.md section 3 (BL-053, all rows)
    yy = np.arange(len(labs))
    axs[2].barh(yy + 0.2, old, height=0.38, color="#bbb", label="BL-053 (h1_rev5.md 3)")
    axs[2].barh(yy - 0.2, new, height=0.38, color="#1f6fb4", label="BL-056")
    axs[2].axvline(1.0, color="k", lw=1)
    axs[2].set_yticks(yy, labs, fontsize=8)
    axs[2].set_xlabel("min over every row: SF / goal (1.5 strength, 1.15 fatigue)")
    for i, v in enumerate(new):
        axs[2].text(v + 0.03, i - 0.2, f"{v:.2f}", va="center", fontsize=7)
    for i, v in enumerate(old):
        axs[2].text(v + 0.03, i + 0.2, f"{v:.2f}", va="center", fontsize=7, color="#666")
    axs[2].legend(fontsize=7, loc="upper right")
    axs[2].set_xlim(0, max(new + old) * 1.2)
    axs[2].set_title("US2 clevis joint, every row", fontsize=9)
    SCREENS = ROOT / "outputs" / "screens"
    SCREENS.mkdir(parents=True, exist_ok=True)
    path = SCREENS / "20261121_BL056_4.png"
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return str(path.relative_to(ROOT))
