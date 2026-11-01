"""Material / process evaluation of the verified generative frame bodies (printed_frame_study.md).

Inputs: outputs/genframe/<tag>_verify.json(+npz) from huntkit.gendesign.frame_study. Verified stresses are
for the FACTORED HA-LS-1 loads (stress <= allowable is the check) and, for one isotropic material, do not
depend on E; stiffness results are for E = 1 MPa and scale with 1/E (pure designs). Hybrid designs were
solved with the PA6-CF / rod modulus ratio and are evaluated for that matrix only.

Requirements applied to every material (HA-LS-1 rev B + this study):
- strength: knocked-down allowable / factored stress >= 1 (99th-percentile element stress, load-patch and
  clamp elements excluded). FDM: layer-wise failure index with the Z (interlayer) strength, best build
  orientation per segment.
- stiffness: frame torsion and static-carry deflection (magnitude of the stay-top socket displacement relative
  to the hip pivot) within 20 % of the v2 tube frame (Weber fraction for
  stiffness 0.23, Jones & Hunter 1990: a smaller change is not reliably felt; a larger one is).
- creep: 150 lb static carry held 8 h at 40 C: deflection growth with the 40 C / wet modulus and the 8 h
  creep modulus ratio; sustained stress <= creep-rupture ratio x knocked-down strength.
- fatigue: 1e5 cycles of 0 -> 1.6 g x 68 kg: peak stress <= fatigue ratio x knocked-down strength.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import frame_topopt as ft
from .frame_study import MATRIX_FOR_HYBRID_E, OUT

TUBE_FRAME_G = 569.2         # geometry.yaml weight budget: frame.yaml v2 + printed Ti hip-pivot mount
KEPT_G = {                   # v2 items the printed body does NOT replace (frame.yaml mass_g)
    "carbon crown (legs 73.8 + top bar 17.9 + spine 26.0)": 117.7,
    "crown rack + pawl housing + pulley guides": 44.0,
    "UHMWPE bushings (4)": 16.7,
    "spine clamp": 6.0,
    "SLM Ti hip-pivot mount (gendesign_results.yaml)": 20.2,
}
REPLACED_G = {               # v2 items the printed body replaces
    "stays": 80.0, "mid bar": 17.9, "upper bar": 22.1, "lumbar pan + flanges": 110.4, "lumbar pad-up": 12.5,
    "carbon wraps + gussets": 64.6, "adhesive": 29.1, "foot boots": 28.0,
}
STIFF_LIMIT = 0.80
G_FAT = 1.6
INSERTS_G = 12.0             # ASSUMPTION: brass heat-set inserts, rod/dowel bond, joint bolts (2 x M5 x 2)


def kept_g():
    return sum(KEPT_G.values())


def load_verified(tag: str) -> dict:
    v = json.loads((OUT / f"{tag}_verify.json").read_text())
    v["meta"] = json.loads((OUT / f"{tag}.json").read_text())
    return v


def static_stress(v, key="static_carry|19"):
    """Unfactored 1.0 g static-carry 99th-percentile von Mises (E-normalized field)."""
    s = v["stress"][key]
    return s["vm99"] / s["factor"]


def governing(v):
    k = max(v["stress"], key=lambda k: v["stress"][k]["vm99"])
    return k, v["stress"][k]["vm99"]


def fdm_orientation(tag: str, m: ft.PrintMaterial) -> dict:
    """Best layer normal (x, y = flat on the plate, z) by the 99th-percentile layer failure index."""
    z = np.load(OUT / f"{tag}_verify.npz")
    ex = z["exclude"]
    out = {}
    for a, nm in ((1, "y (frame face on the plate)"), (0, "x (on edge)"), (2, "z (upright)")):
        fi = ft.layer_failure_index(z["env_s"], z["env_t"], a, m.s_xy, m.s_z, m.knock)
        out[nm] = float(np.percentile(fi[~ex], 99))
    best = min(out, key=out.get)
    return {"by_normal": out, "best": best, "fi99": out[best]}


@dataclass
class Eval:
    tag: str
    material: str
    label: str
    process: str
    body_g: float
    frame_g: float
    sf_strength: float
    sf_fatigue: float
    sf_creep_rupture: float
    torsion_rel: float           # printed / tube
    carry_rel: float             # tube deflection / printed deflection (stiffness ratio)
    creep_defl_mm: float         # stay-top aft deflection after 8 h at 40 C under 150 lb
    tube_defl_mm: float
    hot_truck: str
    cold: str
    cost_usd: float
    orientation: str = ""
    passes: bool = False
    notes: str = ""


def evaluate(tag: str, m: ft.PrintMaterial, tube: dict, rods_g: float = 0.0, E_override=None) -> Eval:
    v = load_verified(tag)
    hybrid = v["meta"]["hybrid"]
    vol_cm3 = v["volume_mm3"] / 1e3
    body = vol_cm3 * m.rho / 1e3 + rods_g + INSERTS_G
    frame = body + kept_g()
    gk, s_gov = governing(v)
    if m.anisotropic:
        o = fdm_orientation(tag, m)
        sf = 1.0 / o["fi99"]
        orient = o["best"]
    else:
        sf = m.knock * m.s_xy / s_gov
        orient = "any (isotropic powder bed)"
    s_eff = sf * s_gov                 # knocked-down allowable expressed as an equivalent von Mises stress
    s1 = static_stress(v)
    sf_fat = m.fat * s_eff / (G_FAT * s1)
    sf_rup = m.rupture * s_eff / s1
    E = E_override or (0.95 * m.E if m.anisotropic else m.E)
    st = v["stiff"]
    if hybrid:
        k_t = st["torsion_Nm_per_deg"] / st["E_ref"] * MATRIX_FOR_HYBRID_E
        d_c = np.hypot(st["carry_dy_mm"], st["carry_dz_mm"]) * st["E_ref"] / MATRIX_FOR_HYBRID_E
    else:
        k_t = st["torsion_Nm_per_deg"] / st["E_ref"] * E
        d_c = np.hypot(st["carry_dy_mm"], st["carry_dz_mm"]) * st["E_ref"] / E
    torsion_rel = k_t / tube["torsion_Nm_per_deg"]
    d_tube = np.hypot(tube["carry_dy_mm"], tube["carry_dz_mm"])
    carry_rel = d_tube / max(abs(d_c), 1e-9)
    if hybrid:   # rods carry most of the stiffness: creep only softens the matrix share (ASSUMPTION: 50 %)
        creep_d = abs(d_c) * (0.5 + 0.5 / (m.E_hot * m.creep8h))
    else:
        creep_d = abs(d_c) / (m.E_hot * m.creep8h)
    hot = ("OK: HDT {:.0f} C at 0.45 MPa >> 60 C, unloaded; anneal FDM parts >= 80 C so they do not relax/warp"
           .format(m.hdt_c) if m.hdt_c >= 100 else "RISK")
    cold_ij = m.impact_kj_m2 * m.impact_cold_ratio
    cold = (f"notched Charpy ~{cold_ij:.1f} kJ/m2 at -20 C (est.)" if m.impact_kj_m2 else "no published notched value") + \
        ("; brittle-risk" if 0 < cold_ij < 3.0 else "")
    cost = body * m.cost_per_g if m.process.startswith(("MJF", "SLS", "SLM", "continuous")) else \
        (body - rods_g - INSERTS_G) * m.cost_per_g
    e = Eval(tag=tag, material=m.id, label=m.label, process=m.process, body_g=body, frame_g=frame,
             sf_strength=sf, sf_fatigue=sf_fat, sf_creep_rupture=sf_rup, torsion_rel=torsion_rel, carry_rel=carry_rel,
             creep_defl_mm=creep_d, tube_defl_mm=d_tube, hot_truck=hot, cold=cold, cost_usd=cost,
             orientation=orient)
    e.passes = (sf >= 1.0 and sf_fat >= 1.0 and sf_rup >= 1.0 and torsion_rel >= STIFF_LIMIT and carry_rel >= STIFF_LIMIT)
    return e


def lightest_passing(tags: list, m: ft.PrintMaterial, tube: dict, rods_g=0.0) -> dict:
    """Evaluate the sweep; interpolate (log-log in body mass) the lightest body meeting every requirement.
    Beyond the sweep, extrapolate with the fitted power laws and flag it."""
    rows = [evaluate(t, m, tube, rods_g) for t in tags]
    rows.sort(key=lambda r: r.body_g)
    mass = np.array([r.body_g for r in rows])
    crit = {"strength": np.array([r.sf_strength for r in rows]), "fatigue": np.array([r.sf_fatigue for r in rows]),
            "creep_rupture": np.array([r.sf_creep_rupture for r in rows]),
            "torsion": np.array([r.torsion_rel for r in rows]) / STIFF_LIMIT,
            "carry": np.array([r.carry_rel for r in rows]) / STIFF_LIMIT}
    need = {}
    for k, y in crit.items():
        need[k] = _threshold_mass(mass, y)
    mreq = max(need.values())
    gov = max(need, key=need.get)
    return {"rows": rows, "need_g": need, "body_g": mreq, "frame_g": mreq + kept_g(), "governing": gov,
            "extrapolated": bool(mreq > mass.max())}


def as_dict(e: Eval) -> dict:
    return asdict(e)


def _threshold_mass(mass, y):
    """Smallest body mass from which every heavier design meets y >= 1: linear interpolation between the
    last failing and the first passing design of that final passing run; power-law extrapolation (fit of the
    two heaviest designs) if even the heaviest fails, or of the two lightest if all pass."""
    ok = y >= 1.0
    if ok.all():          # passes even at the lightest verified design: report that design (no downward
        return float(mass[0])    # extrapolation - the fixed sleeves / bosses set a floor)
    if not ok[-1]:
        if len(mass) >= 2 and y[-1] > y[-2] > 0:
            b = np.log(y[-1] / y[-2]) / np.log(mass[-1] / mass[-2])
            return float(mass[-1] * (1.0 / y[-1]) ** (1 / b)) if b > 0.05 else float("inf")
        return float("inf")
    i = len(ok) - 1
    while i > 0 and ok[i - 1]:
        i -= 1
    m0, m1, y0, y1 = mass[i - 1], mass[i], y[i - 1], y[i]
    return float(m0 + (1.0 - y0) * (m1 - m0) / (y1 - y0))
