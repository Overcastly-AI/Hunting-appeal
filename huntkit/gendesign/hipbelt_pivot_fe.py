"""Re-check of the SLM Ti hipbelt pivot mount with the fore-aft lumbar push (structural-fea-engineer, 2026-11-09).

Why: the generative-design check (``lugs.py``, ``analysis/generative_design.md``: SF/req 8.6, fatigue 19.7) took the pivot
load as the frame-model reaction at node HP. In that model the back-pad grid (P11..P33) reacts the pack's fore-aft
couple, so every HP load set has **Fy = 0** (``outputs/gendesign/stage_specs.pkl``). With hipbelt concept B the lumbar
pad sits on the centre plate, which hangs on the pivot pin, so the lumbar push H goes through the pin
(``analysis/hipbelt_fit.md`` section 6 flag).

What this does: rebuilds the same lug (same SIMP run, same three optimisation load sets, deterministic, so the same
geometry), then runs the independent fine-mesh verification under every original load set PLUS, for each one, the
same set with the lumbar push added along the pin axis (+y, toward the frame) and the moment of that push about the pin
for a pad pressure centroid ``+/- E_PAD_MM`` above / below the pin.

H per case = rated mass x g x CG-aft / (yoke z - 120) (``hipbelt.py`` couple), CG per HA-LS-1 rev C.

    python -m huntkit.gendesign.hipbelt_pivot_fe        # ~10-15 min, writes outputs/gendesign/pivot_recheck.json
"""
from __future__ import annotations

import copy
import json
import pickle
import time
from pathlib import Path

import numpy as np

from huntkit.gendesign import hipbelt as hb

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "outputs" / "gendesign"
OUT = WORK / "pivot_recheck.json"
E_PAD_MM = 20.0          # ASSUMPTION: lumbar pressure centroid within +/-20 mm of the pin (terraced wedge, tilt)

# case -> (mass kg, g at the case, CG aft mm) under rev C. side-hill: 1.6 g, the full sagittal couple (conservative).
CASE_H = {
    "static_carry": (68.0, 1.0, 205.0),
    "drop_2p5g": (68.0, 2.0, 205.0),
    "side_hill_torsion": (68.0, 1.6, 205.0),
    "meat_shelf_heavy_low": (68.0, 2.0, 190.0),     # rev B key name; rev C meat_straps CG 190
    "meat_straps": (68.0, 2.0, 190.0),
    "tall_load": (68.0, 2.0, 185.0),
    "tall_load_posts": (68.0, 2.0, 185.0),
    "overload_haul": (91.0, 1.6, 190.0),
}


def lumbar_push_n(case: str, torso: int) -> float:
    m, g, cg = CASE_H[case]
    return m * hb.G * g * cg / (hb.YOKE_Z[int(torso)] - hb.LUMBAR_Z)


def augment(spec, e_pad: float = E_PAD_MM):
    """Copy of the hip_pivot_mount spec with, for every load set, two extra sets: + H (Fy) and Mx = -e H, e = +/-e_pad."""
    sp = copy.deepcopy(spec)
    pin = next(s for s in sp.sockets if s.name == "pivot_pin")
    new = {}
    for key, v in list(pin.loads.items()):
        case, torso, _ = key.split("|")
        if case not in CASE_H:
            continue
        H = lumbar_push_n(case, int(torso))
        for tag, e in (("Hup", e_pad), ("Hdn", -e_pad)):
            k2 = f"{key}|{tag}"
            v2 = np.array(v, float).copy()
            v2[1] += H
            v2[3] += -e * H              # M = r x F, r = (0, 0, e), F = (0, H, 0) -> Mx = -e H
            new[k2] = (v2, case)
            sp.case_req[k2] = spec.case_req[key]
            if key in spec.static_keys:
                sp.static_keys.append(k2)
    for k2, (v2, case) in new.items():
        pin.loads[k2] = v2
    return sp


def run(log=print) -> dict:
    from .lugs import optimize_lug, strength_check, verify_lug
    t0 = time.time()
    d = pickle.load(open(WORK / "stage_specs.pkl", "rb"))
    spec = next(s for s in d["specs"] if s.name == "hip_pivot_mount")
    fat_g = float(d["fatigue_g"])
    cached = pickle.load(open(WORK / "lug_hip_pivot_mount_slm_ti.pkl", "rb"))
    vf = float(cached["volfrac"])
    log(f"re-optimising hip_pivot_mount slm_ti at vf {vf} (original load sets) ...")
    opt = optimize_lug(spec, "slm_ti", volfrac=vf)
    sp2 = augment(spec)
    opt2 = dict(opt)
    opt2["all_keys"] = list(opt["all_keys"]) + [k for k in sp2.case_req if k.endswith(("Hup", "Hdn"))]
    log(f"verifying {len(opt2['all_keys'])} load sets ...")
    ver = verify_lug(sp2, "slm_ti", opt2)
    chk = strength_check(sp2, "slm_ti", ver, fat_g)
    rows = chk["rows"]
    orig = [r for r in rows if not r["key"].endswith(("Hup", "Hdn"))]
    withH = [r for r in rows if r["key"].endswith(("Hup", "Hdn"))]
    # fatigue with the static set WITHOUT H (reproduces the record) and WITH H (the B belt)
    stat0 = [k for k in spec.static_keys]
    sk0 = max(stat0, key=lambda k: np.linalg.norm(spec.sockets[1].loads[k][:3]))
    from huntkit.fea.materials_bridge import get_material
    mat = get_material("ti_6al_4v_slm")
    Se = float(mat.require("fatigue_limit_asbuilt_hip_mpa"))
    Su = float(mat.require("ultimate_strength_design_mpa"))

    def fat(key):
        dd = ver["per_key"][key]
        smax = dd["vm_p99"] / dd["req"] * fat_g
        sa = smax / 2
        sar = sa / max(1 - sa / Su, 1e-3)
        return {"key": key, "smax_mpa": smax, "sf": Se / sar}
    statH = [k for k in sp2.static_keys if k.endswith(("Hup", "Hdn")) and k in ver["per_key"]]
    fat0 = fat(sk0) if sk0 in ver["per_key"] else None
    fatH = min((fat(k) for k in statH), key=lambda r: r["sf"]) if statH else None
    out = {
        "what": "SLM Ti hip-pivot mount, fine-mesh re-verification with the lumbar push H on the pin (hipbelt B)",
        "e_pad_mm": E_PAD_MM,
        "volfrac": vf, "n_solid_fine": ver["n_solid_fine"], "h_fine": ver["h_fine"],
        "allow_mpa": chk["allow"],
        "min_sf_over_req_original": min(r["sf_over_req"] for r in orig),
        "governing_original": min(orig, key=lambda r: r["sf_over_req"])["key"],
        "min_sf_over_req_with_H": min(r["sf_over_req"] for r in withH),
        "governing_with_H": min(withH, key=lambda r: r["sf_over_req"])["key"],
        "fatigue_original": fat0, "fatigue_with_H": fatH,
        "record": {"sf_static": cached["sf_static"], "fatigue_sf": cached["fatigue"]["sf"]},
        "rows": [{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()} for r in rows],
        "H_n": {f"{c}|{t}": round(lumbar_push_n(c, t), 1) for c in CASE_H for t in (15, 19, 23)},
        "seconds": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1, default=float))
    log(f"done in {out['seconds']} s: original {out['min_sf_over_req_original']:.2f}, with H "
        f"{out['min_sf_over_req_with_H']:.2f}; fatigue {fat0 and fat0['sf']:.1f} -> {fatH and fatH['sf']:.1f}")
    return out


if __name__ == "__main__":
    run()
