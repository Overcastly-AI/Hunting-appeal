"""Run a frame through the load cases, joint checks and fatigue screen -> a study dict for
``report.report``."""
from __future__ import annotations

import numpy as np

from .fatigue import life, sn_from_material
from .joints import check_frame_joints
from .load_cases import LoadCase, pack_standard

# ASSUMPTIONS for the fatigue screen (requirement: >= 1e5 cycles at 1.2 g carry)
FATIGUE = {
    "g": 1.2,
    "cycles_required": 1e5,
    "Kt_metal": 2.0,          # ASSUMPTION: stress concentration at fittings / sleeve ends
    "cfrp_fi_limit": 0.5,     # ASSUMPTION: CFRP 1e5-cycle strength ~50 % of knocked-down static
    "adhesive_frac": 0.3,     # ASSUMPTION: bond fatigue threshold ~30 % of lap-shear strength
}


def fatigue_screen(static_result, joints_static=None, cfg=None) -> dict:
    """Pulsating (R = 0) cycles 0 -> 1.2 x static-carry stress."""
    c = {**FATIGUE, **(cfg or {})}
    scale = c["g"] / static_result.meta["case"].g_factor
    rows = []
    mdefs = {str(md.get("id", i)): md for i, md in enumerate(static_result.model["members"])}
    from .materials_bridge import get_material
    for m in static_result.members:
        mat = mdefs[m["id"]].get("material")
        metal = False
        if "von_mises" in m and mat is not None:
            mm = get_material(mat)
            metal = bool(mm.get("ultimate_strength_mpa")) and mm.category != "composites" and \
                not mm.get("design_allowable_mpa")
        if metal:
            curve = sn_from_material(mat)
            smax = c["Kt_metal"] * scale * m["von_mises"]
            n = life(smax, 0.0, curve)
            rows.append({"member": m["id"], "group": m["group"], "kind": "metal", "smax": smax,
                         "life": n, "ok": n >= c["cycles_required"]})
        else:
            if m["group"] == "lumbar_plate_shear":
                continue
            fi = scale * (m["fi"] if "fi" in m else (1 / m["sf"] if m["sf"] > 0 else np.inf))
            rows.append({"member": m["id"], "group": m["group"], "kind": "cfrp", "fi": fi,
                         "sf": c["cfrp_fi_limit"] / fi if fi > 0 else np.inf,
                         "ok": fi <= c["cfrp_fi_limit"]})
    jrows = []
    for j in joints_static or []:
        tau = scale * j["tau_avg"]
        lim = c["adhesive_frac"] * j["allow"] / 0.8   # allow already has hot/wet 0.8; use dry strength
        jrows.append({"joint": j["joint"], "member": j["member"], "tau": tau, "limit": lim,
                      "sf": lim / tau if tau > 0 else np.inf, "ok": tau <= lim})
    return {"members": rows, "joints": jrows, "cfg": c}


def run_study(frame_model: dict, cases: list[LoadCase] | None = None, label: str | None = None) -> dict:
    ls1 = cases is None and frame_model.get("topology") == "pack5200_crown"
    if ls1:
        # Pack 5200 frames are judged against HA-LS-1 (designs/pack_5200/analysis/load_standard.md);
        # the extension-post case needs the posts model, so it is left to the sizing.
        from .load_standard import FATIGUE as LS1_FATIGUE, ls1_cases
        cases = [c for c in ls1_cases() if c.name != "tall_load_posts"]
    cases = cases or pack_standard()
    results, joints = {}, {}
    for c in cases:
        r = c.run(frame_model)
        results[c.name] = r
        joints[c.name] = check_frame_joints(r, frame_model.get("joints", []))
    fat = None
    if "static_carry" in results:
        fat = fatigue_screen(results["static_carry"], joints.get("static_carry"),
                             {"g": LS1_FATIGUE["g"]} if ls1 else None)
    return {"label": label or frame_model.get("name", "frame"), "frame": frame_model,
            "results": results, "joints": joints, "fatigue": fat}


def summarize(study: dict) -> list[dict]:
    rows = []
    for name, r in study["results"].items():
        req = r.meta["required_sf"]
        js = study["joints"].get(name) or []
        jmin = min(js, key=lambda j: j["sf_avg"]) if js else None
        cm = r.critical_member
        rows.append({"case": name, "min_sf": r.min_sf, "required_sf": req, "critical": cm["id"],
                     "critical_group": cm["group"], "buckling": r.buckling_sf,
                     "joint_sf": jmin["sf_avg"] if jmin else np.inf,
                     "joint_peak_sf": jmin["sf_peak"] if jmin else np.inf,
                     "joint": jmin["joint"] if jmin else "",
                     "pass": (r.min_sf >= req and (not jmin or jmin["sf_avg"] >= req)
                              and (r.buckling_sf >= 3.0 * req / 2.0)),
                     "hip_fraction": r.meta.get("hip_fraction")})
    return rows
