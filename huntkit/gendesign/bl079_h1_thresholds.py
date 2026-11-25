"""BL-079: coupon thresholds for the RELEASED PAHT-CF H1 (as is), and the layer-time floor at the real profile.

BL-077 (``bl077_paht``) gave coupon pass lines for H1c only. This module answers: at what measured hot/wet B-basis
values (Z, SBS / interlayer shear, fatigue ratio, modulus ratio) does the released H1 pass every HA-LS-1 rev C row
(strength, static fatigue, R1, creep, z 234 joint, US2 lug, US2 clevis, hip mount, lash, buckling)?

Method (exact on the BL-077 machinery, no surrogate):

- The layer allowables move together by a factor ``f``: s_z = f x 18.92 MPa (the code's s_z = min(Z, tau / 0.6),
  BL-077 ``materials``), i.e. Z = f x 19.66 and tau = f x 11.35 MPa. XY stays at the booked hot/wet 43.14 MPa
  (ASSUMPTION XY-HELD: no coupon here measures the XY tensile B-basis; CA-4-PAHT's flexural strength is for the record).
- Each H1 basis is solved ONCE (``bl070_h1p.solve``, 4 bases) and every factor is evaluated on the same fields
  (``h1_sleeve.evaluate`` + ``frame_h1.joint_check`` on the cut sections), so the f = 1 column reproduces BL-077's
  H1 hot/wet rows exactly (test). The US2 lug submodel, the clevis and the hip inserts are re-run per factor.
- The fatigue ratio ``g`` (measured / booked 0.30) enters every fatigue row linearly (fatigue = fat x allowable in
  every rule; checked on one point, f 1 / g 1.2).
- Threshold of a row = the smallest f on the grid at which it reaches its goal, linearly interpolated between the
  bracketing grid points. The margin is concave in f (a max of terms, only the layer terms scale), so the chord lies
  below the curve and the interpolated f is never lower than the true one (conservative). Lines are then rounded UP
  to 0.1 MPa (consistent conservative rounding, BL-079 task 5).

Layer time (task 2): ``layer_time()`` re-derives the frame-half median layer time at the BUILD_H1 PAHT profile
(0.20 mm layers) with the BL-053 rule (``bl073_hotwet.layer_time_s`` at LAYER_H 0.2).

Run: ``python -m huntkit.gendesign.bl079_h1_thresholds [scan | apply]``. ``apply`` writes the new keys into
designs/pack_5200/iter1/frame/bl077.json (and the BL-079 corrections) without re-running BL-077.
"""
from __future__ import annotations

import contextlib
import json
import math
import time
from pathlib import Path

import numpy as np

from . import bl070_h1p as P
from . import bl073_hotwet as B
from . import bl077_paht as X
from . import frame_iter1 as FI

REPO = P.REPO
OUT = REPO / "outputs" / "bl079"
SCAN_JSON = OUT / "scan_h1.json"
FACTORS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0)
G_CHECK = 1.2                     # one fatigue-ratio point to confirm the fatigue rows are linear in the ratio
LAYER_H_PAHT = 0.20               # BUILD_H1 section 3: PAHT-CF frame profile 0.20 mm layers


def key(f: float, g: float = 1.0) -> str:
    return f"paht_hw_f{int(round(f * 100))}" + ("" if g == 1.0 else f"_g{int(round(g * 100))}")


_MATERIALS = X.materials          # the unpatched BL-077 materials (scaled() patches X.materials)


def scaled_materials() -> dict:
    base = _MATERIALS()["paht_hw"]
    out = {}
    for f in FACTORS:
        out[key(f)] = {**base, "label": f"PAHT-CF hot/wet, layer allowables x {f:g}", "s_z": base["s_z"] * f}
    out[key(1.0, G_CHECK)] = {**base, "label": f"PAHT-CF hot/wet, fatigue ratio x {G_CHECK:g}",
                              "fat": base["fat"] * G_CHECK}
    return out


@contextlib.contextmanager
def scaled(mat: str):
    """X.paht(mat) with the scaled materials registered (X.materials is a module global read at call time)."""
    orig = X.materials
    X.materials = lambda: {**_MATERIALS(), **scaled_materials()}
    try:
        with X.paht(mat, out=OUT) as m:
            yield m
    finally:
        X.materials = orig


def _mats() -> list:
    return [key(f) for f in FACTORS] + [key(1.0, G_CHECK)]


def scan_body(log=print) -> dict:
    """Body + z 234 joint rows of the released H1 raster at every factor: one solve per basis."""
    from . import frame_h1 as H1
    from . import h1_sleeve as S
    OUT.mkdir(parents=True, exist_ok=True)
    res = json.loads(SCAN_JSON.read_text()) if SCAN_JSON.exists() else {}
    body = res.setdefault("body", {})
    solid = X.raster_of("h1")
    for b in P.BASES:
        todo = [m for m in _mats() if b not in body.get(m, {})]
        if not todo:
            continue
        t0 = time.time()
        fields = P.solve(solid, b)
        secs = H1.cut_sections(fields, H1.JOINT)
        for mat in todo:
            with scaled(mat):
                with P.material(mat):
                    r = S.evaluate(fields)
                    jc = H1.joint_check(None, secs=secs)
            body.setdefault(mat, {})[b] = {"min": {k: float(v) for k, v in r["min"].items()},
                                           "joint_strength": float(jc["min_strength"]),
                                           "joint_fatigue": float(jc["min_fatigue"])}
        SCAN_JSON.write_text(json.dumps(res, indent=1))
        if log:
            log(f"[{time.strftime('%H:%M:%S')}] {b}: {len(todo)} materials ({time.time() - t0:.0f} s)")
        del fields
    return res


def body_rows(mat_res: dict) -> dict:
    """BL-077 reduction (bl070_h1p.summary): static = min of fine_sm8 / fine / beam, R1 = fine_sm8.cyc."""
    st = [b for b in P.BASES if not b.endswith(".cyc")]
    cy = "fine_sm8.cyc"
    s = {k: min(mat_res[b]["min"][k] for b in st) for k in ("strength", "fatigue", "creep")}
    return {"strength": round(s["strength"], 3), "static_fatigue": round(s["fatigue"], 3),
            "R1": round(mat_res[cy]["min"]["fatigue"], 3),
            "creep": round(min(s["creep"], mat_res[cy]["min"]["creep"]), 3),
            "joint_strength": round(min(mat_res[b]["joint_strength"] for b in P.BASES), 3),
            "joint_fatigue": round(min(mat_res[b]["joint_fatigue"] for b in P.BASES), 3)}


def scan_parts(log=print) -> dict:
    """US2 lug submodel, US2 clevis and the H1 hip inserts at every factor."""
    res = json.loads(SCAN_JSON.read_text()) if SCAN_JSON.exists() else {}
    parts = res.setdefault("parts", {})
    for mat in _mats():
        if mat in parts:
            continue
        t0 = time.time()
        with scaled(mat):
            lug = P.us2_lug(mesh=None, mat=mat, tag="h1")
            clev = P.us2_clevis(mat)
            hip = P.hip_inserts(mat)
        parts[mat] = {"lug_strength": lug["design_min"]["strength"], "lug_fatigue": lug["design_min"]["fatigue"],
                      "clevis_strength": clev["share_1"]["all_rows_min"]["strength"],
                      "clevis_fatigue": clev["share_1"]["all_rows_min"]["fatigue"],
                      "clevis_fatigue_06": clev["share_0.6"]["all_rows_min"]["fatigue"],
                      "hip_ins_strength": hip["abs_z"]["min_sf"]["strength"],
                      "hip_ins_fatigue": hip["abs_z"]["min_sf"]["fatigue"],
                      "hip_ins_creep": hip["abs_z"]["min_sf"]["creep"]}
        SCAN_JSON.write_text(json.dumps(res, indent=1))
        if log:
            log(f"[{time.strftime('%H:%M:%S')}] parts {mat}: {parts[mat]} ({time.time() - t0:.0f} s)")
    return res


# ================================================================================================ thresholds
GOALS = {"strength": 1.0, "static_fatigue": 1.0, "R1": 1.0, "creep": 1.0, "joint_strength": 1.0,
         "joint_fatigue": 1.0, "lug_strength": 1.5, "lug_fatigue": 1.15, "clevis_fatigue_06": 1.15,
         "hip_ins_strength": 1.5, "hip_ins_fatigue": 1.15, "hip_ins_creep": 1.5}
FATIGUE_ROWS = {"static_fatigue", "R1", "joint_fatigue", "lug_fatigue", "clevis_fatigue", "clevis_fatigue_06",
                "hip_ins_fatigue"}
LABEL = {"strength": "strength (min of 3 static bases)", "static_fatigue": "fatigue, static carry",
         "R1": "fatigue, cinch-cycled (R1)", "creep": "creep (static / cinch-cycled, min)",
         "joint_strength": "z 234 joint strength", "joint_fatigue": "z 234 joint fatigue",
         "lug_strength": "US2 lug strength", "lug_fatigue": "US2 lug fatigue",
         "clevis_fatigue_06": "US2 clevis fatigue (share 0.6, design; share gate CLEVIS-SHARE-B-PAHT)",
         "hip_ins_strength": "hip inserts strength", "hip_ins_fatigue": "hip inserts fatigue",
         "hip_ins_creep": "hip inserts creep"}


def table(res: dict) -> dict:
    """{row: [margin at each factor]} at the booked fatigue ratio."""
    out = {}
    for f in FACTORS:
        m = key(f)
        r = {**body_rows(res["body"][m]), **res["parts"][m]}
        for k, v in r.items():
            out.setdefault(k, []).append(float(v))
    return out


def f_needed(ms: list, goal: float, fs=FACTORS) -> float | None:
    """Smallest f where the margin reaches ``goal`` (chord interpolation: conservative for a concave margin);
    None if it does not reach it on the grid."""
    if ms[0] >= goal:
        return 1.0
    for i in range(1, len(fs)):
        if ms[i] >= goal:
            f0, f1, m0, m1 = fs[i - 1], fs[i], ms[i - 1], ms[i]
            return f0 + (goal - m0) / (m1 - m0) * (f1 - f0)
    return None


def up(x: float, step: float = 0.1) -> float:
    """Round UP to ``step`` (pass lines on measured strengths: never lenient)."""
    return round(math.ceil(x / step - 1e-9) * step, 10)


BODY_KEYS = ["strength", "static_fatigue", "R1", "creep", "joint_strength", "joint_fatigue", "lug_strength",
             "lug_fatigue", "clevis_fatigue_06"]
INS_KEYS = ["hip_ins_strength", "hip_ins_fatigue", "hip_ins_creep"]
XY_LIMITED = {"clevis_fatigue": "US2 clevis fatigue at share 1.0 (XY hole bearing): gated by CLEVIS-SHARE-B-PAHT, "
                                "as on H1c"}


def _route_layer(tab: dict, keys: list, g: float = 1.0) -> dict:
    """Layer allowables x f with every fatigue row x g: the f each row needs (None: saturates below goal)."""
    need = {}
    for k in keys:
        ms = [m * (g if k in FATIGUE_ROWS else 1.0) for m in tab[k]]
        need[k] = f_needed(ms, GOALS[k])
    miss = [k for k, v in need.items() if v is None]
    if miss:
        return {"reachable": False, "saturate_below_goal": miss,
                "at_fmax": {k: round(tab[k][-1] * (g if k in FATIGUE_ROWS else 1.0), 3) for k in miss}}
    k = max(need, key=need.get)
    return {"reachable": True, "f": round(need[k], 4), "governing": k}


def thresholds(res: dict | None = None) -> dict:
    """The coupon lines of the released H1, three ways (sleeved hip and the 8 inserts kept, each):

    A. layer route: measured Z / SBS scale the layer allowables (f); fatigue ratio and XY as booked;
    B. ratio route: as A, with a measured fatigue ratio g x 0.30 credited to EVERY term (in-plane too);
    C. all-allowables route: XY, Z and SBS all F x booked (every rule is homogeneous in the allowables, so every
       margin is exactly F x its f 1 value)."""
    res = res or json.loads(SCAN_JSON.read_text())
    b = X.basis()
    z_hw, tau_hw, xy_hw = b["hw"]["z"], b["hw"]["tau"], b["hw"]["xy"]
    tab = table(res)
    gk = key(1.0, G_CHECK)
    gr = {**body_rows(res["body"][gk]), **res["parts"][gk]}
    lin = {k: round(gr[k] / tab[k][0], 4) for k in FATIGUE_ROWS if k in gr and tab[k][0] > 0}
    rows = {k: {"goal": GOALS[k], "at_f1": tab[k][0], "at_fmax": tab[k][-1],
                "f_need": (lambda v: None if v is None else round(v, 4))(f_needed(tab[k], GOALS[k]))}
            for k in GOALS}
    out = {"basis": {"z_hw": z_hw, "tau_hw": tau_hw, "xy_hw": xy_hw}, "factors": list(FACTORS), "table": tab,
           "rows": rows, "fatigue_linearity_g": {"g": G_CHECK, "ratio": lin},
           "xy_limited": {k: {"why": v, "at_f1": tab[k][0], "at_fmax": tab[k][-1], "goal": 1.15}
                          for k, v in XY_LIMITED.items()}}
    for mode, keys in (("sleeved", BODY_KEYS), ("inserts", BODY_KEYS + INS_KEYS)):
        fat = [k for k in keys if k in FATIGUE_ROWS]
        A = _route_layer(tab, keys)
        if A["reachable"]:
            A.update({"z_b_mpa": up(z_hw * A["f"]), "sbs_b_mpa": up(tau_hw * A["f"])})
        # B: the least ratio at which every fatigue row can reach goal (at the grid's top f), then the f it needs
        g_min = max(GOALS[k] / tab[k][-1] for k in fat)
        r_min = up(0.30 * g_min, 0.01)
        Bm = _route_layer(tab, keys, r_min / 0.30)
        Bm.update({"fat_ratio_min": r_min})
        if Bm["reachable"]:
            Bm.update({"z_b_mpa": up(z_hw * Bm["f"]), "sbs_b_mpa": up(tau_hw * Bm["f"])})
        curve = []
        for r in (0.30, 0.32, 0.35, 0.40, 0.45, 0.50, r_min, 0.55, 0.60):
            q = _route_layer(tab, keys, r / 0.30)
            curve.append({"fat_ratio": r, "f": q.get("f"), "z_b_mpa": up(z_hw * q["f"]) if q["reachable"] else None,
                          "sbs_b_mpa": up(tau_hw * q["f"]) if q["reachable"] else None})
        curve = sorted({c["fat_ratio"]: c for c in curve}.values(), key=lambda c: c["fat_ratio"])
        # C: every allowable x F (exact: margins are homogeneous of degree 1 in the allowables)
        Fk = {k: GOALS[k] / tab[k][0] for k in keys}
        kc = max(Fk, key=Fk.get)
        F = Fk[kc]
        C = {"F": round(F, 4), "governing": kc, "xy_b_mpa": up(xy_hw * F), "z_b_mpa": up(z_hw * F),
             "sbs_b_mpa": up(tau_hw * F)}
        out[mode] = {"layer_route": A, "ratio_route": {**Bm, "curve": curve}, "all_route": C,
                     "reachable_by_kit_coupons": bool(A["reachable"])}
    return out


# ================================================================================================ layer time
def layer_time(stl_dir: Path | None = None, layer_h: float = LAYER_H_PAHT) -> dict:
    """Median / min layer time of each frame half at ``layer_h`` (BL-053 rule, bl073_hotwet.layer_time_s). The
    released H1 halves (print/frame_h1) and H1c (iter1/frame/h1c)."""
    import trimesh
    saved = B.LAYER_H
    B.LAYER_H = layer_h
    try:
        out = {}
        for lab, d in (("H1", REPO / "designs" / "pack_5200" / "print" / "frame_h1"), ("H1c", X.STL_DIR)):
            for h in ("h1_lower_flat", "h1_upper_flat"):
                r = B.layer_time_s(trimesh.load(d / f"{h}.stl", force="mesh"))
                out[f"{lab}:{h}"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()
                                     if not isinstance(v, (list, np.ndarray))}
        return out
    finally:
        B.LAYER_H = saved


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = (argv or sys.argv[1:]) or ["scan"]
    if a[0] == "scan":
        scan_parts()
        scan_body()
        print(json.dumps(thresholds(), indent=1))
    elif a[0] == "layer":
        print(json.dumps(layer_time(), indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
