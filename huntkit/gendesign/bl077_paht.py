"""BL-077: PAHT-CF H1 under the cost cap (docs/RUBRIC.md 1b; DECISIONS 2026-11-25 "PPA-CF H1-P parked, back to PAHT").

What this module does (machinery reused from ``bl070_h1p`` / ``bl073_hotwet`` / ``bl076``):

1. **Honest basis (review 8 B-2, M-1, M-4 applied to PAHT).** ``basis()``: B-basis tolerance factor at the TDS n
   (``bl073_hotwet.k_factor``), a combined hot (40 C) x wet knock-down from cited PA12-CF data (Bambu dry / wet bending
   pairs; Ciganas et al. 2026 PA12 CF15 UTS 23 / 40 C; Tg-shift reading of that curve), an interlayer-shear basis
   (von Mises tau = sigma / sqrt 3 on the layer-normal strength, was 0.6 x Z with no source). The record's design
   basis (XY 88, Z 47 TDS means x 0.8) is ``paht_rec``; the honest one is ``paht_hw``.
2. **Rows before / after.** Every HA-LS-1 rev C row of the H1 print re-run on ``paht_hw``: whole body (the BL-058
   check on the released STL raster, 4 bases), z 234 joint, US2 lug submodel, US2 clevis, hip inserts, lash pulls;
   buckling is unchanged (the booked E_hot 0.6 is below the cited 0.72 x wet).
3. **Candidates under the cap** (``candidates()``), lightest-cheapest first, each checked on the exported STL raster.
4. **Coupons and cost** (``coupons()``, ``cost_table()``).

Units N, mm, MPa, g, USD. Run: ``python -m huntkit.gendesign.bl077_paht [base | report]``.
"""
from __future__ import annotations

import contextlib
import json
import math
from pathlib import Path

import numpy as np

from . import bl070_h1p as P
from . import bl073_hotwet as B
from . import frame_iter1 as FI

REPO = P.REPO
OUT = REPO / "outputs" / "bl077"
DESIGN = P.DESIGN
STL_DIR = DESIGN / "h1c"
REC_JSON = DESIGN / "bl077.json"
REC_MD = DESIGN / "bl077.md"
SCREENS = P.SCREENS
SHOT = "20261125_bl077_"
RHO = 1.06e-3                     # g/mm3 (record density 1060)
BODY_G = P.PAHT_BODY_G            # 1069.32 g: h1_assembled.stl + clevises (bl058.json stl)

# ================================================================================================ basis (task 1)
# Bambu PAHT-CF TDS. Two published sheets disagree; the LOWER mean of each property is taken (record rule).
TDS_V2 = {"xy": (88.0, 7.0), "z": (64.0, 3.0), "src": "Bambu PAHT-CF TDS V2.0 (cdn.shopify.com, record source 1)"}
TDS_V3 = {"xy": (92.0, 7.0), "z": (47.0, 5.0), "tg_dsc_c": 70.0, "hdt_045_c": 194.0, "hdt_18_c": 170.0,
          "water_pct": 0.88, "bend_xy": (125.0, 7.0), "bend_z": (61.0, 5.0), "elong_xy": 8.4, "elong_z": 4.1,
          "src": "Bambu PAHT-CF TDS V3.0 (uwaterloo.ca RPC mirror, file name 'v2'; read 2026-11-25): dry, annealed "
                 "80 C 12 h; ISO 527 / ISO 178; Tg 70 C (DSC 10 C/min)"}
N_TDS = 5                          # ASSUMPTION B-BASIS-N5: ISO 527-1 minimum specimen count (the TDS gives no n)
# Wet: Bambu publishes dry / wet bending pairs for PAHT-CF (saturated at 25 C / 55 % RH) and a property decline of
# 12-18 % after water absorption (crea3d.com product page quoting the Bambu table, read 2026-11-25).
WET_BEND = {"xy": (125.0, 115.0), "z": (61.0, 49.0), "decline_pct": (12.0, 18.0)}
# Hot: Ciganas J., Kalinauskis T., Cigane U., "Thermo-Mechanical and Fatigue Behavior of 3D-Printed PA12 CF15 for
# Engineering Application", Polymers 18(5):563 (2026), doi 10.3390/polym18050563, Table 3 (Fiberlogy PA12 CF15,
# printed flat, +-45, dried 80 C 12 h): UTS 49.07 / 40.31 / 32.70 / 26.60 MPa, E 2.18 / 1.56 / 1.00 / 0.82 GPa at
# 23 / 40 / 60 / 80 C; Tg (DMA tan delta, 1 Hz) about 55 C.
CIG_T = (23.0, 40.0, 60.0, 80.0)
CIG_UTS = (49.07, 40.31, 32.70, 26.60)
CIG_E = (2.18, 1.56, 1.00, 0.82)
CIG_TG = 55.0
T_HOT, T_ROOM = 40.0, 23.0
MATRIX_FRAC = 0.8                  # ASSUMPTION MATRIX-FRAC (as BL-073): Bambu does not publish the fibre fraction
TAU_RATIO = 1.0 / math.sqrt(3.0)   # interlayer shear / layer-normal strength (von Mises); the code rule had 0.6
TAU_RATIO_RULE = 0.6               # frame_topopt.layer_failure_index hard-codes 0.6 x s_z


def _interp(xs, ys, x: float) -> float:
    """Piecewise linear, linear extrapolation off either end."""
    xs, ys = list(xs), list(ys)
    if x <= xs[1]:
        i = 0
    elif x >= xs[-2]:
        i = len(xs) - 2
    else:
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    return ys[i] + (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) * (x - xs[i])


def wet_ratio() -> dict:
    """Wet / dry at 23-25 C from the Bambu pairs: XY bending 115 / 125 = 0.92, Z bending 49 / 61 = 0.803; Bambu's
    stated decline 12-18 % caps the XY reading at 0.82 (the lowest reading is taken, review 8 rule)."""
    xy_b = WET_BEND["xy"][1] / WET_BEND["xy"][0]
    z_b = WET_BEND["z"][1] / WET_BEND["z"][0]
    floor = 1.0 - WET_BEND["decline_pct"][1] / 100.0
    return {"xy_bending": round(xy_b, 3), "z_bending": round(z_b, 3), "decline_floor": round(floor, 3),
            "xy": math.floor(min(xy_b, floor) * 100) / 100, "z": math.floor(min(z_b, floor) * 100) / 100}


def hot_ratio() -> dict:
    """40 C / 23 C strength ratio for WET PAHT-CF. Three readings of the Ciganas PA12 CF15 curve, the lowest taken:
    (a) direct, dry: UTS 40 / 23 C; (b, c) read at the same distance below Tg, with the Bambu Tg (70 C dry, DSC)
    depressed by water: PA66 rate 11.3 C per wt % on the matrix water (0.88 / 0.8) and the ForTii PPA rate 26.5 C per
    wt % on the compound water 0.88 % (the BL-073 rates, bl073_hotwet.TG_DROP_PER_PCT)."""
    out = {"direct_40_23_dry": round(CIG_UTS[1] / CIG_UTS[0], 4)}
    for lab, (d, on) in B.TG_DROP_PER_PCT.items():
        w = TDS_V3["water_pct"] / MATRIX_FRAC if on == "matrix" else TDS_V3["water_pct"]
        tg_w = TDS_V3["tg_dsc_c"] - d * w
        t23 = CIG_TG - (tg_w - T_ROOM)
        t40 = CIG_TG - (tg_w - T_HOT)
        out[lab] = {"drop_c_per_pct": round(d, 1), "water_basis": on, "water_pct": round(w, 3),
                    "tg_wet_c": round(tg_w, 1), "read_at_c": [round(t23, 1), round(t40, 1)],
                    "ratio": round(_interp(CIG_T, CIG_UTS, t40) / _interp(CIG_T, CIG_UTS, t23), 4)}
    lo = min([out["direct_40_23_dry"]] + [v["ratio"] for v in out.values() if isinstance(v, dict)])
    out["chosen"] = math.floor(lo * 100) / 100
    out["modulus_40_23"] = round(CIG_E[1] / CIG_E[0], 3)
    return out


def basis() -> dict:
    """Record basis vs the honest hot/wet B-basis. Allowables in MPa (already knocked)."""
    k = B.k_factor(N_TDS)
    xy_mean = min(TDS_V2["xy"][0], TDS_V3["xy"][0])
    xy_sd = TDS_V2["xy"][1] if TDS_V2["xy"][0] <= TDS_V3["xy"][0] else TDS_V3["xy"][1]
    z_mean, z_sd = min((TDS_V2["z"], TDS_V3["z"]), key=lambda v: v[0])
    w, h = wet_ratio(), hot_ratio()
    xy_b, z_b = xy_mean - k * xy_sd, z_mean - k * z_sd
    xy_hw = xy_b * w["xy"] * h["chosen"]
    z_hw = z_b * w["z"] * h["chosen"]
    rec = {"xy": 0.8 * 88.0, "z": 0.8 * 47.0, "tau": 0.8 * 0.6 * 47.0}
    hw = {"xy": xy_hw, "z": z_hw, "tau": TAU_RATIO * z_hw}
    return {"k": round(k, 4), "n": N_TDS, "xy_mean": xy_mean, "xy_sd": xy_sd, "z_mean": z_mean, "z_sd": z_sd,
            "xy_b": round(xy_b, 2), "z_b": round(z_b, 2), "wet": w, "hot": h,
            "knock_xy": round(w["xy"] * h["chosen"], 4), "knock_z": round(w["z"] * h["chosen"], 4),
            "tau_ratio": round(TAU_RATIO, 4), "rec": {k_: round(v, 2) for k_, v in rec.items()},
            "hw": {k_: round(v, 2) for k_, v in hw.items()},
            "scale": {k_: round(hw[k_] / rec[k_], 4) for k_ in rec},
            "E_hot_booked": 0.6, "E_hot_cited": round(h["modulus_40_23"] * w["xy"], 3)}


def materials() -> dict:
    """frame_comp_d-shaped dicts. ``paht_rec``: the record basis (= frame_comp_d paht_fdm). ``paht_hw``: knock 1.0
    with the knocked allowables folded in; the code's interlayer rule is 0.6 x s_z, so s_z is set to tau_hw / 0.6
    (the layer-normal term then reads 3.8 % harsh: conservative, and layer-normal is 0 % of the R1 top 1 %)."""
    b = basis()
    base = {"label": "PAHT-CF", "rule": "layer", "rho": 1060.0, "E": 3860.0, "fat": 0.30, "rup": 0.40, "usd_g": 0.08}
    return {"paht_rec": {**base, "label": "PAHT-CF record basis", "s_xy": 88.0, "s_z": 47.0, "knock": 0.8},
            "paht_hw": {**base, "label": "PAHT-CF hot/wet B-basis", "s_xy": b["hw"]["xy"],
                        "s_z": min(b["hw"]["z"], b["hw"]["tau"] / TAU_RATIO_RULE), "knock": 1.0}}


def joint_material(mat: str) -> dict:
    m = materials()[mat]
    return {"s_xy": m["s_xy"], "s_z": m["s_z"], "knock": m["knock"], "fat": m["fat"], "E": 3860.0, "E_hot": 0.6}


@contextlib.contextmanager
def paht(mat: str = "paht_hw", out: Path | None = None):
    """Route the bl070 machinery (check_body, material(), lug / clevis / lash wrappers) onto a PAHT basis, caching in
    ``out`` (default outputs/bl077)."""
    saved = (P.materials, P.joint_material, P.e_buckle, P.OUT, P.ppa_record)
    orig_m, orig_r = P.materials, P.ppa_record
    P.materials = lambda: {**orig_m(), **materials()}
    P.joint_material = lambda m=mat: joint_material(m) if m in materials() else saved[1](m)
    P.e_buckle = lambda m=mat: FI.E_PAHT * 0.6 * 0.7
    P.ppa_record = lambda: {**orig_r(), "E": 3860.0, "rho": 1060.0, "E_hot": 0.6, "E_hot_hw": 0.6}
    P.OUT = out or OUT
    P.OUT.mkdir(parents=True, exist_ok=True)
    try:
        yield materials()[mat]
    finally:
        P.materials, P.joint_material, P.e_buckle, P.OUT, P.ppa_record = saved


def check(name: str, solid: np.ndarray, mat: str = "paht_hw", bases=P.BASES, orient: bool = False,
          log=print) -> dict:
    """bl070_h1p.check_body on a PAHT basis (cached outputs/bl077/check_<name>_<mat>.json)."""
    with paht(mat):
        return P.check_body(name, solid, bases=bases, mat=mat, orient=orient, log=log)


# ================================================================================================ re-tune (candidate R)
MAT = "paht_hw"
EXPORT_DIR = OUT / "export_stl"     # working export of each step (the chosen one is copied to STL_DIR)


def raster_of(name: str) -> np.ndarray:
    if name == "h1":
        return FI.baseline_solid()
    return np.load(OUT / f"{name}_solid.npz")["solid"]


def util_hw(name: str, bases=P.LOOP_BASES, key: str = "util") -> np.ndarray:
    with paht(MAT):
        return P.util_field(name, MAT, bases, key=key)


@contextlib.contextmanager
def export_ctx(stl_dir: Path = EXPORT_DIR):
    """bl070 export path into ``stl_dir`` with the BL-073/076 hip boss (8 x D5.5 through holes, flat back, spot face
    for the two 6061 arc plates) and the BL-073 z 234 bolt positions; the bl070 exact-feature mask is reused."""
    saved = P.STL_DIR
    OUT.mkdir(parents=True, exist_ok=True)
    fm = OUT / "feature_mask.npz"
    if not fm.exists():
        import shutil
        shutil.copy(REPO / "outputs" / "bl070" / "feature_mask.npz", fm)
    P.STL_DIR = stl_dir
    stl_dir.mkdir(parents=True, exist_ok=True)
    try:
        with paht(MAT), B.plate_hook():
            yield
    finally:
        P.STL_DIR = saved


def flat_pinches(stl_dir: Path) -> list:
    """Non-manifold spots of the laid-flat halves (the STL round trip after lay_flat + orient_on_bed can pinch where
    the frame-coordinate halves are closed), mapped back to frame coordinates by the exact affine fit of the
    export's own chain (split at z 234, frame_h1.lay_flat, h1_bedfit.orient_on_bed) on the assembled mesh."""
    import trimesh
    from . import frame_h1 as H1
    from . import h1_bedfit as BF
    from .frame_topopt import split_mesh
    m = trimesh.load(stl_dir / "h1_assembled.stl", force="mesh")
    out = []
    for half, fn in zip(split_mesh(m, H1.JOINT.z), ("h1_lower_flat.stl", "h1_upper_flat.stl")):
        p = stl_dir / fn
        if not p.exists():
            continue
        pts = P.pinch_points(p)
        if not pts:
            continue
        f, _bed = BF.orient_on_bed(H1.lay_flat(half))
        A = np.c_[half.vertices, np.ones(len(half.vertices))]
        T = np.linalg.lstsq(A, f.vertices, rcond=None)[0]
        out += list(np.linalg.solve(T[:3, :].T, (np.asarray(pts) - T[3, :]).T).T)
    return out


def export_step(prev: str, name: str, u_lo: float, u_hi: float, n_thin: int = 1, grow: bool = True,
                log=print) -> dict:
    """bl073_hotwet.export_step_hw on the PAHT hot/wet utilisation: resize ``prev`` (h1 = the released raster),
    export through the release path, re-raster the export, check it on every basis. Body mass at PAHT density."""
    import shutil
    import trimesh
    ps = raster_of(prev)
    u = util_hw(prev)
    d, _r0, add = P.resize_step(ps, u, 0.0, u_hi, grow=grow, thin=False)
    d, rem, _a = P.resize_step(d, u, u_lo, 99.0, grow=False, thin=n_thin > 0, keep=add)
    for _ in range(max(n_thin - 1, 0)):
        d, r2, _a = P.resize_step(d, u, u_lo, 99.0, grow=False, thin=True, keep=add)
        rem |= r2
    fused = []
    info = None
    with export_ctx():
        for _ in range(8):
            try:
                info = P.export(d, log=None)
                break
            except RuntimeError as e:
                if log:
                    log(f"  export retry: {str(e)[-160:]}")
                pts = P.pinch_points(P.STL_DIR / "h1_assembled.stl") or flat_pinches(P.STL_DIR)
                if not pts:
                    raise
                cen = FI._base()["cen"]
                k = len(fused)
                for q in pts:
                    near = np.linalg.norm(cen - q, axis=1) < 3.5 + 1.5 * k
                    if k < 2:                      # first fuse the pinch (bl070 rule) ...
                        f = near & P.allowed_add()
                        d = d | f
                        fused.append({"at_mm": [round(float(v), 1) for v in q], "voxels": int(f.sum()), "how": "fuse"})
                    else:                          # ... then put the previous step's body back around it
                        f = near & (d != ps)
                        d = np.where(near, ps, d)
                        fused.append({"at_mm": [round(float(v), 1) for v in q], "voxels": int(f.sum()),
                                      "how": f"revert r {3.5 + 1.5 * k:g}"})
        if info is None:
            raise RuntimeError(f"export of {name} failed after 8 pinch fusions: {fused}")
        np.savez_compressed(OUT / f"{name}_design.npz", solid=d)
        rr, _ri = P.reraster()
        np.savez_compressed(OUT / f"{name}_solid.npz", solid=rr)
        (OUT / f"{name}_export_info.json").write_text(json.dumps(info, default=FI._jd, indent=1))
        keep = OUT / f"stl_{name}"
        keep.mkdir(exist_ok=True)
        for f in P.STL_DIR.glob("*.stl"):
            shutil.copy(f, keep / f.name)
        res = P.check_body(name, rr, bases=P.BASES, mat=MAT, log=log)
    m = trimesh.load(keep / "h1_assembled.stl", force="mesh")
    res["step"] = {"prev": prev, "u_lo": u_lo, "u_hi": u_hi, "grow": grow, "n_thin": n_thin, "basis": MAT,
                   "pinches_fused": fused, "removed": int(rem.sum()), "added": int(add.sum()),
                   "body_g": round(m.volume * RHO, 1), "watertight": bool(m.is_watertight)}
    (OUT / f"check_{name}_{MAT}.json").write_text(json.dumps(res, default=FI._jd))
    if log:
        sm = P.summary(res)
        log(f"  {name}: body {res['step']['body_g']} g, R1 {sm['cinch_cycled']['fatigue']:.3f}, joint fat "
            f"{min(sm['static_cinch']['joint_fatigue'], sm['cinch_cycled']['joint_fatigue']):.3f}, static fat "
            f"{sm['static_cinch']['fatigue']:.3f}, strength {sm['static_cinch']['strength']:.3f}, creep "
            f"{min(sm['static_cinch']['creep'], sm['cinch_cycled']['creep']):.3f}")
    return res


# ================================================================================================ rows (task 1)
ROWS = [  # (key, name, goal)
    ("strength", "strength (min of 3 static bases)", 1.0),
    ("static_fatigue", "fatigue, static carry", 1.0),
    ("R1", "fatigue, cinch-cycled (R1)", 1.0),
    ("creep", "creep (static / cinch-cycled, min)", 1.0),
    ("joint_strength", "z 234 joint strength", 1.0),
    ("joint_fatigue", "z 234 joint fatigue", 1.0),
    ("lug_strength", "US2 lug strength", 1.5),
    ("lug_fatigue", "US2 lug fatigue", 1.15),
    ("clevis_strength", "US2 clevis strength (share 1.0)", 1.5),
    ("clevis_fatigue", "US2 clevis fatigue (share 1.0)", 1.15),
    ("clevis_fatigue_06", "US2 clevis fatigue (share 0.6, design)", 1.15),
    ("hip_strength", "hip mount strength", 1.5),
    ("hip_fatigue", "hip mount fatigue", 1.15),
    ("hip_creep", "hip mount creep", 1.5),
    ("lash", "lash pulls W1 / W2 (p99)", 1.0),
    ("buckling", "buckling, eigen, frame crown held", 1.0),
    ("buckling_record", "buckling, record rule (export raster)", 1.0),
]
GOAL = {k: g for k, _n, g in ROWS}
NAME = {k: n for k, n, _g in ROWS}
# Before = the PAHT H1 rows of record (bl070_h1p.PAHT_H1: bl058.json body, bl065 eigen, lug / clevis / hip / lash
# records), on the record basis (XY 88, Z 47 TDS means x 0.8, interlayer 0.6 x Z).
BEFORE = {"strength": 1.63, "static_fatigue": 1.249, "R1": 0.856, "creep": 1.825, "joint_strength": 1.978,
          "joint_fatigue": 1.05, "lug_strength": 3.34, "lug_fatigue": 1.50, "clevis_strength": 3.02,
          "clevis_fatigue": 1.36, "clevis_fatigue_06": 2.26, "hip_strength": 2.149, "hip_fatigue": 1.208,
          "hip_creep": 2.58, "lash": 4.18, "buckling": 1.336, "buckling_record": 1.022}
EIG_H1 = 1.336             # bl065.json: H1 frame mode, crown held (E 1621 = 3860 x 0.6 x 0.7)


def e_scale() -> float:
    """Buckling modulus on the cited basis over the booked one: (0.716 x 0.82) / 0.6."""
    return basis()["E_hot_cited"] / 0.6


def body_rows(name: str) -> dict:
    """Body rows of a checked raster on paht_hw (P.summary rules: static = min of fine_sm8 / fine / beam)."""
    res = json.loads((OUT / f"check_{name}_{MAT}.json").read_text())
    sm = P.summary(res)
    s, c = sm["static_cinch"], sm["cinch_cycled"]
    return {"strength": s["strength"], "static_fatigue": s["fatigue"], "R1": c["fatigue"],
            "creep": min(s["creep"], c["creep"]),
            "joint_strength": min(s["joint_strength"], c["joint_strength"]),
            "joint_fatigue": min(s["joint_fatigue"], c["joint_fatigue"]),
            "buckling_record": min(s["buckling_record"], c["buckling_record"]),
            "il_share_R1": round(res["fine_sm8.cyc"]["fatigue_top1pct_term_share"]["shear_xy"]
                                 + res["fine_sm8.cyc"]["fatigue_top1pct_term_share"]["shear_yz"], 3),
            "orientation": {b: res[b].get("orientation") for b in P.BASES if res[b].get("orientation")}}


def lug_rows(name: str, mat: str = MAT) -> dict:
    """US2 lug submodel (h1_rev5.lug_check) on the exported mesh of ``name`` (h1 = the released print)."""
    import trimesh
    mesh = None if name == "h1" else trimesh.load(OUT / f"stl_{name}" / "h1_assembled.stl", force="mesh")
    with paht(mat):
        r = P.us2_lug(mesh=mesh, mat=mat, tag=name)
    return {"lug_strength": r["design_min"]["strength"], "lug_fatigue": r["design_min"]["fatigue"],
            "families": r["families"]}


def clevis_rows(mat: str = MAT) -> dict:
    with paht(mat):
        c = P.us2_clevis(mat)
    return {"clevis_strength": c["share_1"]["all_rows_min"]["strength"],
            "clevis_fatigue": c["share_1"]["all_rows_min"]["fatigue"],
            "clevis_fatigue_06": c["share_0.6"]["all_rows_min"]["fatigue"],
            "clevis_strength_06": c["share_0.6"]["all_rows_min"]["strength"], "raw": c}


def lash_rows(name: str, mat: str = MAT) -> dict:
    with paht(mat):
        r = P.lash(raster_of(name), mat=mat, tag=name)
    return {"lash": r["states"]["after"]["margin_p99"]}


# ---------------------------------------------------------------------------------------------- hip mount options
SLEEVE = {"od": 6.35, "id": 5.84, "hole_d": 6.5, "fy_mpa": None, "src": "304 stainless tube 1/4 in OD x 0.010 in "
          "wall, cut to the measured boss depth + 0.05-0.15 mm (pipe cutter + file); ASSUMPTION SLEEVE-TUBE"}
HIP_TORQUE_DRIVER = (0.5, 2.5)     # BUILD_H1 tools: small torque screwdriver 0.5-2.5 N m (the PAHT path already has it)
HIP_TORQUE = 0.6                   # N m with the sleeves (above the driver's bottom end)


def hip_options() -> dict:
    """The hip mount on paht_hw: (a) H1 inserts (h1_closeout.hip_check, HB-6 basis scaled to the hot/wet Z);
    (b) BL-073/076 through-bolts on the two 6061 arc plates at each torque the existing driver can set (bl076.checks
    with the PAHT foundation E_z 2180 x 0.6); (c) the same with compression-limiter sleeves: the preload goes into
    the steel sleeves, the PAHT under the plates carries only the tipping tension T."""
    import math as _m
    from huntkit.materials import load
    from . import bl076 as Y
    from . import frame_h1 as H1
    out = {}
    with paht(MAT) as m:
        h = P.hip_inserts(MAT)
        out["inserts"] = {"min_sf": h["abs_z"]["min_sf"], "capacity_n": h["abs_z"]["capacity"]}
        saved = B.MAT
        B.MAT = MAT
        try:
            d = Y.design()
            plates = {}
            for tq in (0.5, 0.6, 0.8, 1.0):
                c = Y.checks(d, tq, h=0.25)
                plates[f"{tq:g}"] = {"bearing_min": {k: float(v) for k, v in c["bearing_min"].items()},
                                     "bending_sf": c["bending_sf"], "plate_fatigue_sf": c["plate_fatigue_sf"],
                                     "closed_at_walk": c["closed_at_walk"], "pass": c["pass"],
                                     "preload_n": c["preload_n"]}
            out["plates"] = plates
            c0 = Y.checks(d, HIP_TORQUE, h=0.25)
            pc = float(c0["p_per_n_cold"])
            rows = Y.bolt_rows()
        finally:
            B.MAT = saved
        allow = m["knock"] * m["s_z"]
        # window: creep row (preload on the PAHT) vs closure (CLOSE-1.3) for the plates alone
        walk = max(v["T"] for v in rows.values() if v["kind"] == "fatigue")
        f_max_creep = m["rup"] * allow / (1.5 * pc)
        tq_creep = f_max_creep * B.K_LO * 5e-3
        rel = Y.relax_fraction(d)
        tq_close = 1.3 * walk / rel * B.K_HI * 5e-3
        out["plates_window"] = {"creep_needs_torque_max_nm": round(tq_creep, 3),
                                "closure_needs_torque_min_nm": round(tq_close, 3), "window": tq_creep >= tq_close}
        # (c) sleeves
        ss = load("sst_304_annealed")
        fy = float(ss.require("yield_strength_mpa"))
        a_sl = _m.pi / 4 * (SLEEVE["od"] ** 2 - SLEEVE["id"] ** 2)
        f_max = HIP_TORQUE / (B.K_LO * 5e-3)
        ti_f = 0.25 * H1.TI["uts"] * H1.TI["As"]
        srows = {}
        for k, v in rows.items():
            T, kind = v["T"], v["kind"]
            p_ = pc * T
            if kind == "strength":
                sf = allow / p_
            elif kind == "fatigue":
                sf = min(m["fat"] * allow / p_, ti_f / T)
            else:
                sf = m["rup"] * allow / p_
            srows[k] = {"T_n": round(T, 1), "kind": kind, "pressure_mpa": round(p_, 2), "sf": round(sf, 2),
                        "goal": v["goal"]}
        gov = {kd: min(q["sf"] for q in srows.values() if q["kind"] == kd) for kd in ("strength", "fatigue", "creep")}
        from . import h1_closeout as C
        pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
        web = pat["pitch_mm"] - SLEEVE["hole_d"]
        out["sleeves"] = {"torque_nm": HIP_TORQUE, "preload_max_n": round(f_max, 0), "sleeve_area_mm2": round(a_sl, 2),
                          "sleeve_yield_sf": round(fy * a_sl / f_max, 2), "sleeve_fy_mpa": fy,
                          "rows": srows, "min_sf": gov, "pc_mpa_per_n": round(pc, 5),
                          "web_between_holes_mm": round(web, 2), "web_rule_mm": 3.0, "web_ok": web >= 3.0,
                          "pass_rows": all(q["sf"] >= q["goal"] for q in srows.values()),
                          "sleeve_mass_g": round(8 * a_sl * B.BOSS_DEPTH * 7.9e-3, 2)}
    return out


def doubler_bound(name: str = "h1") -> dict:
    """Upper bound of ANY local metal fix (doubler, strap, clamp, PPA insert) at the lumbar strut / hip boss hot spot:
    the margins with the hot-spot regions taken out of the utilisation population altogether (a perfect, infinitely
    stiff and strong local part that also attracts no load from elsewhere: ASSUMPTION PERFECT-LOCAL)."""
    from . import h1_sleeve as S
    g = FI._base()["dom"].grid
    sets = {"lumbar + hip boss": ["lumbar struts / pan", "hip-pivot boss"],
            "lumbar + hip boss + stay sleeve z 160-240": ["lumbar struts / pan", "hip-pivot boss",
                                                          "stay sleeve z 160-240"]}
    out = {}
    for b, key, row in (("fine_sm8.cyc", "fat_u", "R1"), ("fine_sm8", "fat_u", "static_fatigue"),
                        ("fine_sm8", "env", "strength_env")):
        z = np.load(OUT / f"util_{name}_{MAT}_{b}.npz")
        cen = g.elem_centers()[z["idx"]]
        reg = np.array([S.region(p) for p in cen])
        u = z[key]
        o = {"all": round(float(1 / np.percentile(u[u > 0], 99)), 3),
             "voxels_over_1_by_region": {str(k): int(v) for k, v in
                                         zip(*np.unique(reg[u > 1.0], return_counts=True))}}
        for lab, ex in sets.items():
            sel = (u > 0) & ~np.isin(reg, ex)
            o[lab] = round(float(1 / np.percentile(u[sel], 99)), 3)
        out[row] = o
    return out


def candidates(final: str, fin: dict, hip: dict, h1: dict) -> list:
    """Task 2 candidates, lightest-cheapest first, each with its Strong result on the export, cost and mass."""
    db = doubler_bound("h1")
    orient = h1["orientation"]["fine_sm8.cyc"]
    best_o = max(((k, v) for k, v in orient.items() if not k.startswith("y/y")), key=lambda kv: kv[1]["fatigue"])
    ppa = P.materials()
    return [
        {"id": "A", "name": "6061 doubler / strap bolted across the lumbar struts + hip boss",
         "strong": f"FAIL by bound: even a PERFECT local part (lumbar + hip boss + lower stay sleeve removed from the "
                   f"utilisation population) leaves R1 <= {db['R1']['lumbar + hip boss + stay sleeve z 160-240']:.2f}, "
                   f"static fatigue <= {db['static_fatigue']['lumbar + hip boss']:.2f} (lumbar + hip only); the "
                   f"over-utilised voxels are spread over the stays, mid bar and lumbar "
                   f"({sum(db['R1']['voxels_over_1_by_region'].values())} voxels > 1 on the R1 field)",
         "bound": db, "verdict": "rejected (cannot close R1 at any cost)"},
        {"id": "B", "name": "through-bolt clamps (layers in compression) at the lumbar struts",
         "strong": "FAIL by the same bound (a local fix, no better than a perfect one); at the hip boss the clamp is "
                   "candidate F", "verdict": "rejected"},
        {"id": "C", "name": "print orientation (layer normal along x or z per half)",
         "strong": f"FAIL: the as-printed y/y is the best of 5 (R1 {orient['y/y (as printed)']['fatigue']:.3f}; best "
                   f"alternative {best_o[0]} {best_o[1]['fatigue']:.3f}; check_body orient, export raster of H1)",
         "orientation": orient, "verdict": "rejected (keep face-down y/y)"},
        {"id": "D", "name": "reshape within the frozen interfaces (export-space re-tune on the hot/wet utilisation)",
         "strong": f"body rows PASS at {final}: R1 {fin['R1']:.3f}, strength {fin['strength']:.3f}, static fatigue "
                   f"{fin['static_fatigue']:.3f}, joint fatigue {fin['joint_fatigue']:.3f}",
         "verdict": "adopted (H1c)"},
        {"id": "E", "name": "local PPA-CF insert at the hot spot",
         "strong": f"FAIL by the bound of A; and PPA-CF hot/wet Z is only {ppa['ppa_hw']['s_z'] * ppa['ppa_hw']['knock']:.1f} MPa "
                   f"vs PAHT {basis()['hw']['z']:.1f} (x 1.26)", "verdict": "rejected (and one PPA spool is USD 150)"},
        {"id": "F", "name": "hip mount: through-bolts on the BL-076 6061 arc plates + 304 compression-limiter sleeves",
         "strong": f"rows {hip['sleeves']['min_sf']} (goals 1.5 / 1.15 / 1.5); plates alone fail creep "
                   f"({hip['plates']['0.5']['bearing_min']['creep']:.2f} at 0.5 N m, no torque window: creep needs "
                   f"<= {hip['plates_window']['creep_needs_torque_max_nm']:.2f}, closure >= "
                   f"{hip['plates_window']['closure_needs_torque_min_nm']:.2f} N m); inserts fail fatigue "
                   f"{hip['inserts']['min_sf']['fatigue']:.2f}",
         "verdict": "adopted for the hip (web 2.69 mm < 3 mm rule: open item)"},
    ]


def joint_variants(name: str = "r2") -> dict:
    """z 234 joint variants screened on the cut sections of ``name`` (outputs/bl077/run_jointvar2.py: bolt y, boss
    radius, washer OD, frame_h1.boss_envelope), hot/wet basis: the best inside the envelope and what governs it."""
    p = OUT / f"jointvar_{name}.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    ok = {k: v for k, v in d.items() if v["env_ok"]}
    best = max(ok, key=lambda k: ok[k]["fatigue"])
    gov = {b: min(r.items(), key=lambda kv: kv[1]["margin"]) for b, r in ok[best]["rows"].items()}
    base = "yo6.0_yi5.5_rb8.0_wo12.0"
    return {"source": f"cut sections of {name}", "n_variants": len(d), "n_in_envelope": len(ok),
            "baseline": {"key": base, "fatigue": d[base]["fatigue"]},
            "best": {"key": best, "fatigue": ok[best]["fatigue"], "strength": ok[best]["strength"],
                     "governs": {b: [g[0], g[1]["margin"]] for b, g in gov.items()}}}


def open_rows(fin: dict, lug_fams: dict, jv: dict, clevis_share_max: float, hip: dict) -> list:
    """Rows still below goal on H1c and the cheapest option that would close each (none is adopted here)."""
    out = []
    if fin["joint_fatigue"] < 1.0:
        b = jv.get("best", {})
        out.append({"row": "z 234 joint fatigue", "value": fin["joint_fatigue"], "goal": 1.0,
                    "why": "washer bearing (XY), plug shear-out (interlayer) and boss bending at the frozen BL-073 "
                           "joint; the re-tune cannot reach the joint (bosses and holes frozen)",
                    "options": [
                        f"bigger washers + bosses inside frame_h1.boss_envelope (scan of {jv.get('n_in_envelope')} "
                        f"variants on the r2 cut sections): best {b.get('key')} reads {b.get('fatigue')} (plug "
                        "shear-out governs; the upper plug is capped at 16 mm by the z 255 spreader clip). A D16 "
                        "washer is 6061 laser-cut (USD ~2 each in the plate order) but a 1.0 mm Al washer fails bending "
                        "and a 1.6 mm one puts the head 0.1 mm into the clip band: NOT closed",
                        f"coupon route (USD 0 extra, kit CA-5 stub pulls at 40 C on conditioned stubs + CA-3-PAHT SBS): "
                        f"the joint passes if the hot/wet XY B-basis >= {43.14 / fin['joint_fatigue']:.1f} MPa and "
                        f"the SBS B-basis >= {11.35 / fin['joint_fatigue']:.1f} MPa (booked 43.1 / 11.35)",
                        "architecture: move the z 255-265 spreader clip up 6 mm so the upper plug can grow (pack-designer)"]})
    if fin["lug_fatigue"] < 1.15:
        f60 = lug_fams.get("cradle3d|b60", {}).get("fatigue")
        f70 = lug_fams.get("cradle3d|b70", {}).get("fatigue")
        out.append({"row": "US2 lug fatigue", "value": fin["lug_fatigue"], "goal": 1.15,
                    "why": "inner-cheek arm root (x 130, z 154), the frozen lug block; governed by the 40 mm strap "
                           "belly (cradle3d b40)",
                    "options": [f"strap belly >= 60 mm: fatigue {f60} (b70 {f70}); USD 0, but BL-054 found the belly "
                                "cannot be held by feel (needs a sewn stop on the US2 strap: pack-designer)",
                                "grow the US2 inner cheek / buttress again (the BL-053 M-3 fix pattern: h1_rev5 extra "
                                "hulls), needs an interface change: not done here",
                                "6061 strap under the two clevis bolts along the arm (laser-cut, same order): not "
                                "modelled here"]})
    if fin["clevis_fatigue"] < 1.15:
        out.append({"row": "US2 clevis fatigue (share 1.0)", "value": fin["clevis_fatigue"], "goal": 1.15,
                    "why": "hole bearing in the clevis (XY); passes at the design share 0.6",
                    "options": [f"gate: CLEVIS-SHARE-B-PAHT measured share <= {clevis_share_max:.2f}",
                                "304 sleeves (the hip tube, 6.35 mm) in reamed clevis holes: bearing x 1.27, gate "
                                f"<= {min(1.0, clevis_share_max * 1.27):.2f}"]})
    if not hip["sleeves"]["web_ok"]:
        out.append({"row": "hip sleeve-hole web", "value": hip["sleeves"]["web_between_holes_mm"], "goal": 3.0,
                    "why": "review 8 M-2 rule (3 extrusion widths); the D6.5 sleeve holes on the 9.19 mm pitch",
                    "options": ["first article: section the lower half's boss on a spare print and check the web "
                                "fills (no gap) before the frame half", "6-bolt hip pattern (new SLM mount)"]})
    return out


# ================================================================================================ cost (RUBRIC 1b)
CAP_FRAME_USD = 150.0
CAP_PROVING_USD = 150.0
CAP_TOOL_USD = 50.0
SUPPORT_K = 1235.0 / (494.6 + 543.4)   # BUILD_H1 section 3: halves 1038.0 g need up to 1235 g with supports + waste
WASTE_K = 1.08                         # frame_h1_build: + 8 % waste (clevises, pawl, coupons)
PAWL_G = 4.5                           # BUILD_H1: crown_pawl_lp_fdm_pacf 4.2 g -> 4.5 g of filament
SPOOL_G, SPOOL_USD = 1000.0, 80.0      # record cost_usd 80 / kg; TDS: 0.5 and 1 kg spools
PRICE = {   # USD each, with the source of every price
    "ti_m5_din7984": (2.50, "ASSUMPTION (shop price, check at purchase): test kit shopping_list.csv Ti DIN 7984 lines"),
    "a2_m5x35_din7984": (41.79 / 50, "Zoro, M5-0.80 x 35 low-profile SHCS 18-8 (A2), 50 pk USD 41.79, "
                                     "https://www.zoro.com/boltsandnutscom-m5-080-socket-head-cap-screw-low-profile-plain-18-8-stainless-steel-35-mm-length-50-pk-m5c35lshcsa2d-50/i/G214478661/"),
    "nut_a2_m5": (0.10, "ASSUMPTION (shop price, check at purchase): shopping_list.csv"),
    "washer_12": (0.08, "ASSUMPTION (shop price): shopping_list.csv z 234 washer line"),
    "washer_10": (0.05, "ASSUMPTION (shop price): shopping_list.csv clevis washer line"),
    "insert_m5": (0.19, "record insert_heatset_brass_m5 cost_usd (ruthex 50 pcs USD 9.30, 3djake)"),
    "arc_plate": (8.00, "ASSUMPTION RING-PRICE (BL-076 BOM): SendCutSend 6061-T6 .063 in laser cut, no published "
                        "price; SendCutSend order minimum USD 29 (third-party reports) / free US shipping from USD 39 "
                        "(https://sendcutsend.com/), 'about USD 3 per part at 10 off' (steel example, "
                        "https://sendcutsend.com/blog/the-true-cost-of-custom-sheet-metal-parts/)"),
    "tube_304": (7.89, "Zoro, Vita Needle 304 tubing 1/4 in OD x 0.005 in wall x 12 in, USD 7.89 "
                       "(https://www.zoro.com/vita-needle-co-stainless-steel-304-tubing-14-od-x-005-wall-at-12-g1368/i/G1195803/); "
                       "ASSUMPTION TUBE-PRICE: the 0.010 in wall (ID 5.84 mm, clears M5) at the same price"),
    "loctite_243": (9.00, "ASSUMPTION (shop price): BL-074 BOM line, 10 ml bottle (shared by every bolt)"),
}
TOOLS_NEW = [  # new tools for BL-077 (each <= USD 50; the PAHT build already has the 0.5-2.5 N m driver, caliper)
    ("mini tubing cutter (3-22 mm), for the 304 sleeves", 10.0, "ASSUMPTION (shop price, check at purchase)"),
    ("flat needle file + 400 grit paper, sleeve length to the caliper", 6.0, "ASSUMPTION (shop price)"),
]


def _hw(lines: list) -> tuple:
    tot = sum(q * PRICE[k][0] for _n, k, q in lines)
    return round(tot, 2), [{"item": n, "price_key": k, "qty": q, "unit_usd": round(PRICE[k][0], 2),
                            "usd": round(q * PRICE[k][0], 2), "source": PRICE[k][1]} for n, k, q in lines]


SUPPORT_EST_K = (494.6 + 543.4 + 49.0 + 55.3) / (494.6 + 543.4)   # BUILD_H1 section 3: BL-053 support estimate
SCREW_MASS_G = {"ti": 4.43e-3, "a2": 7.93e-3}                      # g / mm3 (Ti-6Al-4V record; A2 / 304)
SCREWS = {"z234": (4, 45.0), "clevis": (4, 35.0), "hip_h1": (8, 12.0), "hip_c": (8, 35.0)}


def screw_vol_mm3(L: float) -> float:
    """DIN 7984 M5: head D8.5 x 3.5 less the s3 x 2.7 socket, shank D4.5 mean (bl073 TI_MM_G rule) x L."""
    return math.pi / 4 * 8.5 ** 2 * 3.5 - 3.0 ** 2 * math.sqrt(3) / 2 * 2.7 + math.pi / 4 * 4.5 ** 2 * L


def filament(halves_g: float, clevis_g: float = 2 * 15.7, high: bool = False) -> dict:
    g = halves_g * (SUPPORT_K if high else SUPPORT_EST_K) + clevis_g * WASTE_K + PAWL_G
    return {"halves_g": round(halves_g, 1), "clevis_g": clevis_g, "filament_g": round(g, 1),
            "basis": "BL-053 support high bound" if high else "BL-053 support estimate",
            "usd": round(g * SPOOL_USD / SPOOL_G, 2)}


def cost_table(halves_h1: float, halves_new: float, coupon_g: float) -> dict:
    """Per-frame cost (cap scope) and first-frame spend for H1 (inserts) and H1c (re-tune + hip plates + sleeves),
    each with Ti or A2 screws. ASSUMPTION COST-SCOPE: 'frame materials' = PAHT filament (body, clevises, pawl,
    supports, waste) + the fasteners and metal parts that join or clamp the printed body (z 234, US2 clevis, hip
    mount screws / inserts / plates / sleeves, threadlocker). The crown (carbon tubes, rack, clamp), the pins, the
    bushings and the SLM Ti hip mount carry over unchanged from every frame path and are outside this cap."""
    out = {}
    for screw in ("ti", "a2"):
        sk = "ti_m5_din7984" if screw == "ti" else "a2_m5x35_din7984"
        common = [("z 234: M5 x 45 DIN 7984", sk, 4), ("z 234: washer 12 x 1 A2", "washer_12", 8),
                  ("z 234: nut DIN 934 A2", "nut_a2_m5", 4), ("US2 clevis: M5 x 35 DIN 7984", sk, 4),
                  ("US2 clevis: washer 10 x 1 A2", "washer_10", 4), ("US2 clevis: nut DIN 934 A2", "nut_a2_m5", 4)]
        h1_hip = [("hip: brass heat-set insert M5", "insert_m5", 8), ("hip: M5 x 12 DIN 7984", sk, 8)]
        c_hip = [("hip: M5 x 35 DIN 7984", sk, 8), ("hip: nut DIN 934 A2", "nut_a2_m5", 8),
                 ("hip: 6061-T6 arc plate .063 in (BL-076 DXF)", "arc_plate", 2),
                 ("hip: 304 tube 1/4 x 0.010 in, 12 in (8 sleeves x 22 mm)", "tube_304", 1)]
        for key, halves, hip in (("H1", halves_h1, h1_hip), ("H1c", halves_new, c_hip)):
            fil = filament(halves)
            hi = filament(halves, high=True)
            hw_usd, hw_lines = _hw(common + hip)
            loc = PRICE["loctite_243"][0]
            per = fil["usd"] + hw_usd + loc / 10.0        # one bottle covers about 10 frames (ASSUMPTION LOC-SHARE)
            out[f"{key}_{screw}"] = {"filament": fil, "filament_high": hi, "hardware_usd": hw_usd, "hardware": hw_lines,
                                     "threadlocker_share_usd": round(loc / 10.0, 2), "per_frame_usd": round(per, 2),
                                     "per_frame_high_usd": round(per - fil["usd"] + hi["usd"], 2),
                                     "cap_usd": CAP_FRAME_USD, "within_cap": bool(per <= CAP_FRAME_USD + 1e-9)}
    n_scr = {"H1": SCREWS["z234"][0] * screw_vol_mm3(45) + 4 * screw_vol_mm3(35) + 8 * screw_vol_mm3(12),
             "H1c": SCREWS["z234"][0] * screw_vol_mm3(45) + 4 * screw_vol_mm3(35) + 8 * screw_vol_mm3(35)}
    out["a2_mass_penalty_g"] = {k: round(v * (SCREW_MASS_G["a2"] - SCREW_MASS_G["ti"]), 1) for k, v in n_scr.items()}
    out["H1"], out["H1c"] = out["H1_ti"], out["H1c_ti"]
    out["cheapest"] = min(("H1c_ti", "H1c_a2"), key=lambda k: out[k]["per_frame_usd"])
    # filament budget the cap leaves for the body at the cheapest H1c hardware
    c = out[out["cheapest"]]
    left = CAP_FRAME_USD - c["hardware_usd"] - c["threadlocker_share_usd"]
    g_left = left / (SPOOL_USD / SPOOL_G) - 2 * 15.7 * WASTE_K - PAWL_G
    out["cap_body_halves_max_g"] = round(g_left / SUPPORT_EST_K, 1)
    # first frame (whole spools, a whole threadlocker bottle, the laser-cut order minimum, coupons, tools)
    tools = sum(t[1] for t in TOOLS_NEW)
    ffs = {}
    for v in ("H1c_ti", "H1c_a2"):
        c = out[v]
        fil_g = c["filament"]["filament_g"] + coupon_g
        spools = math.ceil(fil_g / SPOOL_G)
        plates = max(4 * PRICE["arc_plate"][0], 29.0)        # one spare set; SendCutSend order minimum
        hw_first = c["hardware_usd"] - 2 * PRICE["arc_plate"][0] + plates
        if v.endswith("a2"):
            hw_first += 2 * 41.79 - 16 * PRICE["a2_m5x35_din7984"][0]   # two 50-packs (35 and 45 mm)
        ffs[v] = {"variant": v, "filament_g_frame_plus_coupons": round(fil_g, 1), "spools_1kg": spools,
                  "spools_usd": spools * SPOOL_USD, "hardware_usd": round(hw_first, 2), "laser_order_usd": plates,
                  "threadlocker_usd": PRICE["loctite_243"][0], "new_tools_usd": tools, "tools": TOOLS_NEW,
                  "all_in_usd": round(spools * SPOOL_USD + hw_first + PRICE["loctite_243"][0] + tools, 2)}
    out["first_frame_variants"] = ffs
    out["first_frame"] = min(ffs.values(), key=lambda q: q["all_in_usd"])
    return out


# ================================================================================================ coupons (task 3)
SBS = B.SBS_G                       # ASTM D2344 proportions at t 3 (BL-073)
Z_1BA = {"type": "ISO 527-2 1BA, 3 mm thick (dry pull 64 MPa x 15 mm2 = 960 N, under the 981 N cell)", "gauge_w": 5.0, "t": 3.0, "mm3": 1700.0}
FLEX_MM3 = 80.0 * 10.0 * 4.0
SBS_MM3 = SBS["L"] * SBS["w"] * SBS["t"]
BRIM_K = 1.3                         # ASSUMPTION COUPON-WASTE: brim, purge, ties and skirt on the coupon jobs


def coupons(M: dict, b: dict, lt_s: float) -> list:
    """The PAHT coupon program (review 8 M-3 / M-4 rules): shear-mode fatigue at 40 C on conditioned coupons, layer
    time matched to the frame, B-basis at n 10. ``M``: governing margins of the adopted design on paht_hw."""
    k10 = B.k_factor(10)
    tau, zk = b["hw"]["tau"], b["hw"]["z"]
    m_fat = min(M["R1"], M["joint_fatigue"], M["lug_fatigue"] / 1.15, M["clevis_fatigue_06"] / 1.15,
                M["hip_fatigue"] / 1.15)
    m_z = min(M["R1"], M["joint_fatigue"], M["static_fatigue"])
    m_body = min(M["R1"], M["static_fatigue"])
    s_des = 0.30 * tau / m_fat
    s_test = 1.15 * s_des
    p_sbs = s_test * SBS["w"] * SBS["t"] / 0.75
    need_z = zk / m_z
    cond = ("conditioned to constant mass at 50 C over saturated NaCl (74.4 % RH, Greenspan 1977; above the TDS "
            "55 % RH, conservative) in the kit's conditioning box: weigh daily, done when the mass changes < 0.1 % "
            "in 24 h; record the uptake against the TDS 0.88 %")
    lt = (f"layer time matched to the frame: set Bambu Studio's filament cooling 'slow down for layer cooling' "
          f"layer-time threshold to {lt_s:.0f} s (the median layer time of an H1c half, LAYER-H 0.3 mm) and check "
          f"the layer-time view of the preview; if the minimum speed floor stops it, add a 2-wall ring around the "
          f"coupons (ASSUMPTION LAYER-TIME); log each job's layer time")
    rows = [
        {"id": "CA-3-PAHT", "what": f"Z tensile ({Z_1BA['type']}, printed standing in a 10-bar comb tied at the "
                                    f"grips) and SBS (ASTM D2344 proportions {SBS['L']:g} x {SBS['w']:g} x "
                                    f"{SBS['t']:g}, printed flat: the shear plane is a layer interface); {lt}; hot/wet "
                                    f"set {cond}, tested at 40 +/- 2 C (kit 40 C box); dry set annealed as the frame "
                                    "(BUILD_H1 step 5), tested within 24 h at 23 C",
         "n": {"z_hw": 10, "z_dry": 6, "sbs_hw": 10, "sbs_dry": 6},
         "grams": round((22 * Z_1BA["mm3"] + 22 * SBS_MM3) * 1.06e-3 * BRIM_K, 1),
         "statistic": f"B-basis = mean - k SD, k {k10:.3f} at n 10 (one-sided 90/95 normal tolerance factor, "
                      "CMH-17-1G Vol 1 8.3.4.3; NIST e-Handbook 7.2.6.3)",
         "pass": f"(a) hot/wet Z B-basis >= {zk / m_body:.1f} MPa (= {zk:.2f} / {m_body:.3f}, the body rows R1 and "
                 f"static fatigue); >= {need_z:.1f} MPa also lifts the open z 234 joint fatigue ({M['joint_fatigue']:.3f}) "
                 f"to 1.0; (b) hot/wet SBS B-basis >= {tau / m_body:.1f} MPa (= tau_hw {tau:.2f} / {m_body:.3f}; "
                 f">= {tau / m_z:.1f} for the joint); (c) for the record: hot/wet / dry Z (booked 0.656) and the uptake",
         "settles": "B-BASIS-N5, WET-Z 0.80, HOT-40 0.82, TAU von Mises 0.577", "need_z_mpa": round(need_z, 2),
         "need_sbs_mpa": round(TAU_RATIO * need_z, 2)},
        {"id": "CA-1-PAHT", "what": f"SBS FATIGUE (the governing interlayer mode): the CA-3 SBS bar, {lt}; {cond}; "
                                    "R 0.1, <= 5 Hz, 40 +/- 2 C, on the kit's CA rig (gear motor, lever, 100 kg "
                                    "cell) with a printed SBS jig (span 12, 3 mm pins)",
         "n": {"fatigue": 6, "static": 3}, "grams": round(9 * SBS_MM3 * 1.06e-3 * BRIM_K + 15.0, 1),
         "load": f"Smax (shear) = 1.15 x {s_des:.2f} = {s_test:.2f} MPa, peak load {p_sbs:.0f} N ({p_sbs / 4.448:.0f} "
                 f"lbf), tau = 0.75 P / (b h); {s_des:.2f} = 0.30 x tau_hw {tau:.2f} / governing fatigue margin "
                 f"{m_fat:.3f}",
         "pass": "all 6 run out to 1e5 cycles at 1.15 x Smax (about a factor 4 on life at a Basquin slope near 10); "
                 "the 3 static SBS >= the CA-3-PAHT SBS line",
         "settles": "FAT 0.30 in shear, hot/wet", "smax_test_mpa": round(s_test, 3), "peak_load_n": round(p_sbs, 0)},
        {"id": "CA-4-PAHT", "what": f"ISO 178 3-point bend, XY bars 80 x 10 x 4: 23 C dry; 40 C {cond.split(':')[0]}; "
                                    "60 C dry", "n": {"per_condition": 5},
         "grams": round(15 * FLEX_MM3 * 1.06e-3 * BRIM_K, 1),
         "pass": f"E(40 C conditioned) / E(23 C dry), mean of 5 >= {M['_e_need']:.2f} (the eigen buckling need); for the record the flexural strength ratio vs the booked 0.672",
         "settles": "E-WET 0.587 / modulus_40c_wet 0.6"},
        {"id": "HB-6b-SLV", "what": "the kit's HB-6b hip-mount proof on the first H1c frame, with the 304 sleeves: "
                                    "sleeve proud of the boss back by 0.05-0.15 mm (caliper), plates seated, 0.6 N m",
         "n": {"frames": 1}, "grams": 0.0,
         "pass": "HB-6b pass rule; no witness mark of the plates on the PAHT before the load (the preload sits on "
                 "the sleeves), paint marks unmoved after T5",
         "settles": "SLEEVE-PROUD (the preload stays in the steel)"},
        {"id": "CLEVIS-SHARE-B-PAHT", "what": "the kit's CLEVIS-SHARE B test on the first frame (BL-076 gauge rule "
                                              "share = (u - u0) / (u1 - u0))", "n": {"frames": 1}, "grams": 0.0,
         "pass": f"measured share <= {M['_clevis_share_max']:.2f} (the share at which the clevis hole-bearing "
                 "fatigue row reaches 1.15 on the hot/wet basis)",
         "settles": "CLEVIS-SHARE"},
    ]
    return rows


def coupon_cost(rows: list) -> dict:
    g = sum(r["grams"] for r in rows)
    new = [("printed SBS jig + 3 x 3 mm dowel pins", 6.0, "ASSUMPTION (shop price)"),
           ("NaCl, 1 kg (saturated salt for the conditioning box)", 3.0, "ASSUMPTION (shop price)")]
    fil = g * SPOOL_USD / SPOOL_G
    return {"grams": round(g, 1), "filament_usd": round(fil, 2), "kit_reused": "40 C box, conditioning box, CA rig "
            "(gear motor, lever, 100 kg cell, HX711, Arduino), 3-point bend fixture, caliper (shopping_list.csv)",
            "new_items": new, "new_items_usd": sum(n[1] for n in new),
            "usd": round(fil + sum(n[1] for n in new), 2), "cap_usd": CAP_PROVING_USD}


# ================================================================================================ tornado (M-1)
def tornado(M: dict, il_share: float) -> list:
    """Single-assumption variations on the adopted design's governing rows. Body rows scale by their interlayer
    share (top-1 % term shares of the R1 field) where the variation hits only the interlayer allowable."""
    fat = {"R1", "static_fatigue", "joint_fatigue", "lug_fatigue", "clevis_fatigue_06", "hip_fatigue"}
    zr = {"R1", "static_fatigue", "joint_fatigue", "strength", "creep"}

    def il(k, f):
        s = il_share if k in zr else 0.0
        return 1.0 / (s / f + 1.0 - s)
    var = [("fatigue ratio 0.25 (was 0.30)", "low end of the PA12-CF range in the record (0.25-0.32)",
            "CA-1-PAHT", lambda k: 0.25 / 0.30 if k in fat else 1.0),
           ("interlayer shear 0.5 x Z, Tresca (was von Mises 0.577)", "no PAHT SBS data", "CA-3-PAHT SBS",
            lambda k: il(k, 0.5 / TAU_RATIO)),
           ("wet Z = 0.75 (was 0.80)", "a further 5 % on the Bambu Z bending pair", "CA-3-PAHT hot/wet vs dry",
            lambda k: il(k, 0.75 / 0.80)),
           ("hot 40 C = 0.78 (was 0.82)", "a 5 % harsher Tg-shift reading", "CA-3-PAHT at 40 C",
            lambda k: 0.78 / 0.82 if k in zr | fat else 1.0),
           ("E hot/wet 0.50 (was 0.587 cited / 0.6 booked)", "a further 15 % modulus loss", "CA-4-PAHT",
            lambda k: 0.50 / 0.587 if k == "buckling" else 1.0)]
    return [{"variation": lab, "source": src, "retired_by": ret, "rows": {k: round(v * f(k), 3) for k, v in M.items()}}
            for lab, src, ret, f in var]


# ================================================================================================ figures
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_margins(before: dict, h1: dict, fin: dict, final: str, path: Path) -> str:
    """Margin / goal per row: PAHT H1 on the record basis, PAHT H1 on the hot/wet B-basis, H1c on the hot/wet
    B-basis (exported STL)."""
    plt = _plt()
    keys = [k for k, _n, _g in ROWS]
    fig, ax = plt.subplots(figsize=(8.6, 10.8), dpi=105)
    y = np.arange(len(keys))[::-1]
    h = 0.27
    cols = ("#8a8f98", "#d1495b", "#2a78d6")
    labs = ("H1, record basis (before)", "H1, hot/wet B-basis (honest)", f"H1c {final}, hot/wet B-basis (after)")
    for j, (lab, src) in enumerate(zip(labs, (before, h1, fin))):
        v = [min(src.get(k, np.nan) / GOAL[k], 3.0) for k in keys]
        ax.barh(y + (1 - j) * h, v, h, color=cols[j], label=lab)
        for yy, k in zip(y, keys):
            raw = src.get(k)
            if raw is not None:
                ax.text(min(raw / GOAL[k], 3.0) + 0.02, yy + (1 - j) * h, f"{raw:.2f}", va="center", fontsize=6.5,
                        color=cols[j])
    ax.axvline(1.0, color="#c0392b", lw=1.4)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{NAME[k]} (goal {GOAL[k]:g})" for k in keys], fontsize=7.6)
    ax.set_xlim(0, 3.4)
    ax.set_xlabel("margin / goal (1.0 = goal; bars clipped at 3; labels = margin)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.06), ncol=2, fontsize=8)
    ax.set_title("BL-077 PAHT-CF frame: every HA-LS-1 row, before / honest / after\nhot/wet B-basis: XY 43.1, Z 19.7, "
                 "interlayer shear 11.4 MPa (record: 70.4 / 37.6 / 22.6)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)
    P.shrink_png(path)
    return str(path)


def plot_fix(final: str, r1_h1: float, r1_fin: float, g_h1: float, g_fin: float, hip: dict, path: Path) -> str:
    """The fix in place: R1 utilisation front view H1 vs H1c (max through the depth), where material went (front
    and side), and the hip stack with the sleeves."""
    plt = _plt()
    g = FI._base()["dom"].grid
    cen = FI._base()["cen"]
    s_h1, s_f = raster_of("h1"), raster_of(final)
    u_h1 = util_hw("h1", ("fine_sm8.cyc",), key="fat_u")
    u_f = util_hw(final, ("fine_sm8.cyc",), key="fat_u")
    import textwrap
    fig = plt.figure(figsize=(11.5, 7.6), dpi=95)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.6, 0.42])
    axs = []
    for j, (u, sol, t) in enumerate(((u_h1, s_h1, f"H1, hot/wet: R1 {r1_h1:.2f}"),
                                     (u_f, s_f, f"H1c {final}: R1 {r1_fin:.2f}"))):
        ax = fig.add_subplot(gs[0, j])
        axs.append(ax)
        order = np.argsort(u[sol])
        Pp = cen[sol][order]
        sc = ax.scatter(Pp[:, 0], Pp[:, 2], c=np.clip(u[sol][order], 0, 1.6), s=2.6, cmap="turbo",
                        vmin=0, vmax=1.6, marker="s", linewidths=0)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=10)
        ax.set_xlabel("x mm (front, wearer side)")
    cb = fig.colorbar(sc, ax=axs, shrink=0.75, location="left", pad=0.12)
    cb.set_label("R1 fatigue utilisation (1 = allowable)", fontsize=8)
    ax = fig.add_subplot(gs[0, 2])
    h = float(g.h)
    xs_, zs_ = np.floor(cen[:, 0] / h).astype(int), np.floor(cen[:, 2] / h).astype(int)
    x0, z0 = xs_.min(), zs_.min()
    T = np.zeros((2, xs_.max() - x0 + 1, zs_.max() - z0 + 1))
    for k, sol in enumerate((s_h1, s_f)):
        np.add.at(T[k], (xs_[sol] - x0, zs_[sol] - z0), h)
    dT = np.where((T[0] + T[1]) > 0, T[1] - T[0], np.nan)
    ext = [x0 * h, (xs_.max() + 1) * h, z0 * h, (zs_.max() + 1) * h]
    im = ax.imshow(dT.T, origin="lower", extent=ext, cmap="RdBu_r", vmin=-8, vmax=8, interpolation="nearest")
    ax.set_aspect("equal")
    ax.set_title(f"thickness change front-to-back, mm\n(+{int((s_f & ~s_h1).sum()) * 8 / 1000:.0f} / "
                 f"-{int((s_h1 & ~s_f).sum()) * 8 / 1000:.0f} cm3)", fontsize=9.5)
    ax.set_xlabel("x mm")
    cb2 = fig.colorbar(im, ax=ax, shrink=0.75)
    cb2.set_label("mm added (red) / removed (blue)", fontsize=8)
    ax = fig.add_subplot(gs[1, :])
    ax.axis("off")
    sl = hip["sleeves"]
    paras = [f"Body {g_h1:.0f} g -> {g_fin:.0f} g (PAHT-CF, exported STL). Re-tune on the hot/wet utilisation: grown where "
             f"> 0.8, thinned where < 0.3; every bag / hardware interface frozen.",
             f"Hip mount (the H1 inserts fail fatigue {hip['inserts']['min_sf']['fatigue']:.2f}): 8 x M5 x 35 through the "
             f"D50 boss, two 6061-T6 .063 in arc plates (BL-076 DXF) on the flat back, and 8 x 304 tube sleeves 1/4 x 0.010 "
             f"in cut to the boss depth + 0.05-0.15 mm, so the {HIP_TORQUE} N m preload ({sl['preload_max_n']:.0f} N max) "
             f"sits on the steel. Rows {sl['min_sf']['strength']:.2f} / {sl['min_sf']['fatigue']:.2f} / "
             f"{sl['min_sf']['creep']:.2f} (goals 1.5 / 1.15 / 1.5). Plates alone fail creep at every torque the 0.5-2.5 "
             f"N m driver sets ({hip['plates']['0.5']['bearing_min']['creep']:.2f} at 0.5).",
             f"Open: z 234 joint fatigue and US2 lug fatigue (frozen interfaces); sleeve-hole web "
             f"{sl['web_between_holes_mm']:.2f} mm (< 3 mm rule)."]
    ax.text(0.0, 1.0, "\n".join(textwrap.fill(p_, 150) for p_ in paras), va="top", fontsize=8.6)
    fig.suptitle(f"BL-077 fix in place: H1 -> H1c ({final}), cinch-cycled fatigue, front view", fontsize=11)
    fig.savefig(path, dpi=95)
    plt.close(fig)
    P.shrink_png(path)
    return str(path)


def plot_cost(cost: dict, coup: dict, path: Path) -> str:
    """Per-frame cost (cap scope) H1 vs H1c, and first-frame spend vs the caps."""
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 6.2), dpi=105, gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axs[0]
    ks = ("H1_ti", "H1c_ti", "H1c_a2")
    xs = np.arange(len(ks))
    fil = [cost[k]["filament"]["usd"] for k in ks]
    hw = [cost[k]["hardware_usd"] + cost[k]["threadlocker_share_usd"] for k in ks]
    ax.bar(xs, fil, 0.6, color="#2a78d6", label="PAHT-CF filament (supports + waste)")
    ax.bar(xs, hw, 0.6, bottom=fil, color="#eb6834", label="frame hardware")
    for x, a, b in zip(xs, fil, hw):
        ax.text(x, a + b + 2, f"USD {a + b:.0f}", ha="center", fontsize=10, fontweight="bold")
        ax.text(x, a / 2, f"{a:.0f}", ha="center", color="white", fontsize=9)
        ax.text(x, a + b / 2, f"{b:.0f}", ha="center", color="white", fontsize=9)
    ax.axhline(CAP_FRAME_USD, color="#c0392b", lw=1.6)
    ax.text(-0.45, CAP_FRAME_USD + 3, "cap USD 150", color="#c0392b", fontsize=9, ha="left")
    ax.set_xticks(xs)
    ax.set_xticklabels(["H1 as released\n(Ti screws)", "H1c\n(Ti screws)", "H1c\n(A2 screws)"], fontsize=8.5)
    ax.set_ylabel("USD per frame")
    ax.set_ylim(0, 240)
    ax.set_title("Per frame (cap scope)", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax = axs[1]
    ff = cost["first_frame"]
    items = [("frame (cheapest\nH1c)", cost[cost["cheapest"]]["per_frame_usd"], CAP_FRAME_USD),
             ("proving prints\n(coupons)", coup["usd"], CAP_PROVING_USD),
             ("new tools\n(each <= 50)", ff["new_tools_usd"], None),
             ("first frame\nall-in", ff["all_in_usd"] + coup["new_items_usd"], None)]
    cols = ["#2a78d6", "#5aa469", "#8a8f98", "#444"]
    for i, ((lab, v, cap), c) in enumerate(zip(items, cols)):
        ax.bar(i, v, 0.6, color=c)
        ax.text(i, v + 3, f"USD {v:.0f}", ha="center", fontsize=9.5, fontweight="bold")
        if cap:
            ax.plot([i - 0.38, i + 0.38], [cap, cap], color="#c0392b", lw=1.8)
            ax.text(i, cap - 9, f"cap {cap:.0f}", color="#c0392b", ha="center", fontsize=8)
    ax.set_xticks(range(len(items)))
    ax.set_xticklabels([t[0] for t in items], fontsize=8.5)
    ax.set_ylim(0, max(260, ff["all_in_usd"] * 1.15))
    ax.set_title(f"First frame: {ff['spools_1kg']} x 1 kg spools, laser order min USD 29, "
                 f"threadlocker", fontsize=9.5)
    fig.suptitle("BL-077 cost: PAHT-CF H1c against RUBRIC 1b (the PPA-CF path was about USD 2,100)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)
    P.shrink_png(path)
    return str(path)


# ================================================================================================ record
FINAL = "r3"               # the adopted export step (the lightest that passes every body row): set after the loop
STEPS = ("r1", "r2", "r3")
MASS_G = {"insert": 1.5, "ti_m5x12": 2.102, "nut": 1.1}   # insert record; bl058.json hip_screws x12; review 8 (nut)

ASSUMPTIONS = [
    ("B-BASIS-N5", "The Bambu TDS +/- values are standard deviations of an ISO 527 set of n 5 (the ISO 527-1 minimum; "
     "the TDS gives no n): B-basis k 3.4066 on the lower published mean of each property.", "CA-3-PAHT at n 10"),
    ("WET-PAHT", "Wet / dry = 0.82 XY (Bambu's 12-18 % decline, the 18 % floor; the XY bending pair reads 0.92) and "
     "0.80 Z (the Z bending pair 49 / 61): bending pairs stand in for tensile.", "CA-3-PAHT hot/wet vs dry"),
    ("HOT-40-PAHT", "40 C / 23 C = 0.82 from the Fiberlogy PA12 CF15 UTS curve (Ciganas 2026), the lowest of the "
     "direct and two Tg-shift readings; a PA12-CF15 grade stands in for PAHT-CF.", "CA-3-PAHT at 40 C"),
    ("TAU-VM", "Interlayer shear allowable = Z / sqrt 3 (von Mises), was 0.6 x Z with no source; the frame code's "
     "0.6 x s_z rule is fed s_z = tau / 0.6, so the layer-normal term reads 3.8 % harsh.", "CA-3-PAHT SBS"),
    ("E-WET", "Hot/wet modulus = 0.716 (Ciganas E 40 / 23 C) x 0.82 (wet strength ratio) = 0.587; buckling rows are "
     "scaled by 0.587 / 0.6 from the booked basis.", "CA-4-PAHT"),
    ("FAT-0.30", "PAHT fatigue at 1e5 = 0.30 x the hot/wet B-basis static strength (record ratio, unchanged).",
     "CA-1-PAHT"),
    ("PERFECT-LOCAL", "The bound on any local fix removes the hot-spot regions from the utilisation population and "
     "assumes nothing else changes (a real doubler also attracts load: the bound is optimistic for it).",
     "not needed: the bound already fails"),
    ("SLEEVE-PROUD", "Each 304 sleeve is cut to the measured boss depth + 0.05-0.15 mm, so the 0.6 N m preload sits on "
     "the steel and the PAHT under the plates sees only the hip tipping load (BL-055 model, FLANGE-RIGID).",
     "HB-6b-SLV (no plate witness mark before load, paint marks after T5)"),
    ("SLEEVE-TUBE", "304 tube 1/4 in OD x 0.010 in wall (ID 5.84 mm) is bought as cold-drawn tube; the check uses the "
     "annealed record yield 215 MPa (sleeve SF 1.22 at the K 0.14 preload).", "caliper on receipt; HB-6b-SLV"),
    ("COST-SCOPE", "The cap covers PAHT filament + the fasteners / metal parts that join or clamp the printed body; "
     "crown, pins, bushings and the SLM Ti hip mount carry over and are outside it.", "orchestrator / owner"),
    ("LAYER-TIME", "Bambu Studio's layer-time slowdown can hold each coupon job at the frame's median layer time "
     "without a dummy tower (check the preview's layer-time view; else add a 2-wall ring).", "slicer preview"),
    ("A2-45", "The A2 M5 x 45 DIN 7984 costs the same as the cited A2 M5 x 35 (Zoro 50-pack); the Ti lines are the "
     "kit's USD 2.50 shop-price ASSUMPTION.", "price check at purchase"),
    ("LOC-SHARE", "One 10 ml threadlocker bottle covers about 10 frames (per-frame share USD 0.90).", "n/a (cost)"),
    ("COUPON-WASTE", "Coupon jobs use 1.3 x the coupon volume (brim, ties, purge).", "slicer preview"),
]


def _mass(final: str) -> dict:
    import trimesh
    out = {}
    for nm, d in (("H1", P.REPO / "designs" / "pack_5200" / "print" / "frame_h1"), (final, OUT / f"stl_{final}")):
        g = {k: round(trimesh.load(d / f"{k}.stl", force="mesh").volume * RHO, 1)
             for k in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R")}
        g["body"] = round(trimesh.load(d / "h1_assembled.stl", force="mesh").volume * RHO, 1)
        out[nm] = g
    m35 = MASS_G["ti_m5x12"] + 23.0 * B.TI_MM_G
    hip_h1 = 8 * (MASS_G["insert"] + MASS_G["ti_m5x12"])
    from . import bl076 as Y
    plates = 2 * Y.mass_g(Y.design()) / 2 if False else Y.mass_g(Y.design())
    hip_c = 8 * (m35 + MASS_G["nut"]) + plates + 8 * math.pi / 4 * (SLEEVE["od"] ** 2 - SLEEVE["id"] ** 2) * \
        B.BOSS_DEPTH * 7.9e-3
    out["hip_hardware_g"] = {"H1": round(hip_h1, 2), "H1c": round(hip_c, 2), "delta": round(hip_c - hip_h1, 2),
                             "ti_m5x35_g": round(m35, 2), "plates_g": round(plates, 2)}
    out["frame_delta_g"] = round(out[final]["body"] - out["H1"]["body"] + hip_c - hip_h1, 1)
    return out


def rows_of(name: str, hip_key: str, hip: dict, clev: dict, eig: float) -> dict:
    r = body_rows(name)
    r.update({k: v for k, v in lug_rows(name).items() if k != "families"})
    r.update({k: v for k, v in clev.items() if k.startswith("clevis") and k != "clevis_strength_06"})
    src = hip["inserts"]["min_sf"] if hip_key == "inserts" else hip["sleeves"]["min_sf"]
    r.update({"hip_strength": src["strength"], "hip_fatigue": src["fatigue"], "hip_creep": src["creep"]})
    r.update(lash_rows(name))
    r["buckling"] = round(eig, 3)
    return r


def report(final: str = FINAL, log=print) -> dict:
    import shutil
    b = basis()
    hip = hip_options()
    clev = clevis_rows()
    eig_h1 = EIG_H1 * e_scale()
    eig_p = OUT / f"eigen_{final}.json"
    eig_f = json.loads(eig_p.read_text())["frame_crown_held"] if eig_p.exists() else eig_h1
    h1 = rows_of("h1", "inserts", hip, clev, eig_h1)
    fin = rows_of(final, "sleeves", hip, clev, eig_f)
    steps = {}
    for s in STEPS:
        p = OUT / f"check_{s}_{MAT}.json"
        if p.exists():
            br = body_rows(s)
            st = json.loads(p.read_text()).get("step", {})
            steps[s] = {"body_g": st.get("body_g"), **{k: br[k] for k in ("strength", "static_fatigue", "R1", "creep",
                                                                           "joint_strength", "joint_fatigue")}}
    mass = _mass(final)
    cost = cost_table(mass["H1"]["h1_lower_flat"] + mass["H1"]["h1_upper_flat"],
                      mass[final]["h1_lower_flat"] + mass[final]["h1_upper_flat"], 0.0)
    clevis_share_max = round(min(fin["clevis_fatigue"] * 1.0, fin["clevis_fatigue_06"] * 0.6) / 1.15, 3)
    M = {k: fin[k] for k, _n, _g in ROWS}
    M["_e_need"] = round((basis()["E_hot_cited"] if eig_p.exists() else 0.6) / eig_f, 3)
    M["_clevis_share_max"] = clevis_share_max
    import trimesh
    lt = min(B.layer_time_s(trimesh.load(OUT / f"stl_{final}" / f"{h}.stl", force="mesh"))["median_s"]
             for h in ("h1_lower_flat", "h1_upper_flat"))
    cps = coupons(M, b, lt)
    cc = coupon_cost(cps)
    cost = cost_table(mass["H1"]["h1_lower_flat"] + mass["H1"]["h1_upper_flat"],
                      mass[final]["h1_lower_flat"] + mass[final]["h1_upper_flat"], cc["grams"])
    tor = tornado({k: fin[k] for k, _n, _g in ROWS}, fin["il_share_R1"])
    cands = candidates(final, fin, hip, h1)
    gate_rows = {"clevis_strength": f"CLEVIS-SHARE-B-PAHT: share <= {clevis_share_max:.2f}",
                 "clevis_fatigue": f"CLEVIS-SHARE-B-PAHT: share <= {clevis_share_max:.2f}"}
    jv = joint_variants("r2")
    lugf = lug_rows(final)["families"]
    opens = open_rows(fin, lugf, jv, clevis_share_max, hip)
    rows = []
    for k, n, g in ROWS:
        r = {"key": k, "name": n, "goal": g, "before": BEFORE.get(k), "h1_hw": h1.get(k), "after": fin.get(k),
             "pass_h1_hw": bool(h1.get(k, 0) >= g - 1e-9), "pass_after": bool(fin.get(k, 0) >= g - 1e-9)}
        if not r["pass_after"] and k in gate_rows:
            r["gated_by"] = gate_rows[k]
        rows.append(r)
    fails = [r["name"] for r in rows if not r["pass_after"] and "gated_by" not in r]
    # STLs of the adopted step
    STL_DIR.mkdir(parents=True, exist_ok=True)
    for f in (OUT / f"stl_{final}").glob("*.stl"):
        shutil.copy(f, STL_DIR / f.name)
    md5 = {f.name: __import__("hashlib").md5(f.read_bytes()).hexdigest() for f in sorted(STL_DIR.glob("*.stl"))}
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [plot_margins(BEFORE, h1, fin, final, SCREENS / f"{SHOT}1.png"),
             plot_fix(final, h1["R1"], fin["R1"], mass["H1"]["body"], mass[final]["body"], hip,
                      SCREENS / f"{SHOT}2.png"),
             plot_cost(cost, cc, SCREENS / f"{SHOT}3.png")]
    rec = {"ticket": "BL-077", "date": "2026-11-25", "final": final, "basis": b,
           "record_fix": {"glass_transition_c": {"was": 45, "now": 70, "source": TDS_V3["src"]},
                          "glass_transition_wet_c": 47},
           "rows": rows, "fails_after": fails, "open_rows": opens, "joint_variants": jv, "steps": steps, "candidates": cands, "hip": hip,
           "clevis_share_max": clevis_share_max, "tornado": tor, "coupons": cps, "coupon_cost": cc, "cost": cost,
           "mass": mass, "layer_time_median_s": lt, "stl_dir": str(STL_DIR.relative_to(REPO)), "stl_md5": md5,
           "eigen": {"h1_scaled": round(eig_h1, 3), "final": round(eig_f, 3), "final_solved": eig_p.exists()},
           "assumptions": [{"id": a, "text": t, "settled_by": s} for a, t, s in ASSUMPTIONS],
           "screenshots": [str(Path(s).relative_to(REPO)) for s in shots],
           "kit_needs": kit_needs(cps, cc)}
    REC_JSON.write_text(json.dumps(rec, indent=1, default=FI._jd))
    REC_MD.write_text(write_md(rec))
    if log:
        log(f"BL-077 {final}: fails {fails}; per frame USD {cost['H1c']['per_frame_usd']}; shots {shots}")
    return rec


def kit_needs(cps: list, cc: dict) -> list:
    """What huntkit/manufacturing and the kit generators would need (not edited here: ticket scope)."""
    return [
        "frame_h1_build.py / BUILD_H1: H1c STLs (designs/pack_5200/iter1/frame/h1c/), hip section 12 rewritten for "
        "8 x Ti M5 x 35 through-bolts + 8 DIN 934 nuts + two BL-076 arc plates + 8 x 304 sleeves (1/4 x 0.010 in, cut "
        "to boss depth + 0.05-0.15 mm), torque 0.6 N m with the existing 0.5-2.5 N m driver; drop the heat-set inserts, "
        "the insert guide and HB-6 (inserts no longer used); support / time table from the H1c halves",
        "physical_test_kit: replace CA-1 / CA-3 / CA-4 (PAHT) with CA-1-PAHT (SBS fatigue at 40 C), CA-3-PAHT (Z + SBS, "
        "n 10 hot/wet + 6 dry, layer-time matched), CA-4-PAHT (flex 23 / 40 wet / 60 C), add HB-6b-SLV and "
        "CLEVIS-SHARE-B-PAHT; coupon filament " + f"{cc['grams']:.0f} g",
        "shopping_list: + mini tubing cutter, + 304 tube 1/4 x 0.010 in 12 in, + printed SBS jig pins, + NaCl; "
        "- the Wera 0.3-1.2 N m driver and the 120 C oven (PPA only); PAHT spools 1 kg at the record price",
        "bom: per-frame cost table of bl077.json (cost.H1c) replaces the PPA BOM for the frame",
    ]


def write_md(rec: dict) -> str:
    b, f = rec["basis"], rec["final"]
    L = [f"# BL-077: PAHT-CF H1 under the cost cap (H1c)", "",
         f"Generated by `python -m huntkit.gendesign.bl077_paht report` (data `bl077.json`). Date {rec['date']}. "
         "Rules: HA-LS-1 rev C (`analysis/load_standard.md`), RUBRIC 1 and 1b, review 8 (`analysis/review_20261125_eighth.md`) "
         "B-2 / M-1 / M-4 applied to PAHT. Every body row is checked on the exported STL re-rastered (BL-058 rule, "
         "4 bases). Units N, mm, MPa, g, USD.", "", "## Summary", ""]
    fails = rec["fails_after"]
    c = rec["cost"]
    rmap = {r["key"]: r for r in rec["rows"]}
    L += [f"- **Honest basis.** On the hot/wet B-basis (XY {b['hw']['xy']}, Z {b['hw']['z']}, interlayer shear "
          f"{b['hw']['tau']} MPa against the record's {b['rec']['xy']} / {b['rec']['z']} / {b['rec']['tau']}) the "
          f"released PAHT H1 fails broadly: R1 {rmap['R1']['h1_hw']:.2f}, strength {rmap['strength']['h1_hw']:.2f}, "
          f"static fatigue {rmap['static_fatigue']['h1_hw']:.2f}, z 234 joint fatigue {rmap['joint_fatigue']['h1_hw']:.2f}, "
          f"US2 lug fatigue {rmap['lug_fatigue']['h1_hw']:.2f}, hip inserts fatigue {rmap['hip_fatigue']['h1_hw']:.2f}. "
          "It was never as strong as the record said.",
          f"- **No local fix can close it.** The over-utilised material is spread over both stays, the mid bar, the lumbar "
          f"struts and the hip boss. Even a perfect local part over the lumbar struts, hip boss and lower stay sleeve "
          f"leaves R1 <= {rec['candidates'][0]['bound']['R1']['lumbar + hip boss + stay sleeve z 160-240']:.2f}. "
          "Doublers, clamps, a PPA insert and print orientation are all rejected on Strong.",
          f"- **What closes R1: H1c ({f})**, the export-space re-tune on the hot/wet utilisation (every interface "
          f"frozen), plus a sleeved through-bolt hip mount. R1 {rmap['R1']['after']:.3f}. Body {rec['mass'][f]['body']:.1f} g "
          f"({rec['mass'][f]['body'] / 453.59:.2f} lb), {rec['mass'][f]['body'] - rec['mass']['H1']['body']:+.1f} g on "
          f"H1; frame delta with the hip hardware {rec['mass']['frame_delta_g']:+.1f} g.",
          "- **Rows after:** " + ", ".join(f"{r['name']} {r['after']:.2f}" for r in rec["rows"]
                                            if r["key"] in ("R1", "strength", "static_fatigue", "creep", "joint_fatigue",
                                                            "lug_fatigue", "hip_fatigue", "buckling")) + ".",
          f"- **Still below goal on H1c:** {', '.join(fails) if fails else 'none'}"
          + ("; gated by a test: " + ", ".join(f"{r['name']} ({r['gated_by']})" for r in rec['rows'] if r.get('gated_by'))
             if any(r.get('gated_by') for r in rec['rows']) else "") + ". Section 2b gives the cheapest option for each.",
          f"- **Cost: R1 does NOT close within the USD 150 cap.** H1c costs USD {c['H1c_a2']['per_frame_usd']:.2f} a frame "
          f"with A2 screws (USD {c['H1c_ti']['per_frame_usd']:.2f} with Ti); the released H1 is USD "
          f"{c['H1_ti']['per_frame_usd']:.2f} (Ti). The cap leaves room for about {c['cap_body_halves_max_g']:.0f} g of "
          f"halves (H1c needs {rec['mass'][f]['h1_lower_flat'] + rec['mass'][f]['h1_upper_flat']:.0f} g), and the first re-tune "
          f"step at {rec['steps'].get('r1', {}).get('body_g', 0):.0f} g only reached R1 {rec['steps'].get('r1', {}).get('R1', 0):.2f}. "
          f"**Cheapest option that closes R1: H1c with A2 screws, USD {c['H1c_a2']['per_frame_usd']:.2f} a frame** "
          f"(+{c['a2_mass_penalty_g']['H1c']:.0f} g for the A2 screws). Proving prints USD {rec['coupon_cost']['usd']:.2f} "
          f"(cap 150). First frame all-in USD {c['first_frame']['all_in_usd']:.2f} ({c['first_frame']['variant']}, "
          f"{c['first_frame']['spools_1kg']} spools). No new tool over USD 50.",
          ""]
    L += ["## 1. Basis, before and after (task 1)", "",
          "| item | record (before) | hot/wet B-basis (after) | source |", "|---|---:|---:|---|",
          f"| XY tensile mean / SD | 88 (V2.0) | {b['xy_mean']:g} +/- {b['xy_sd']:g} | TDS V2.0 / V3.0, lower mean |",
          f"| Z tensile mean / SD | 47 (V3.0) | {b['z_mean']:g} +/- {b['z_sd']:g} | TDS V3.0 (V2.0 says 64 +/- 3) |",
          f"| statistic | mean | B-basis, k {b['k']} at n {b['n']} | ASSUMPTION B-BASIS-N5; bl073_hotwet.k_factor |",
          f"| XY / Z B-basis | - | {b['xy_b']} / {b['z_b']} MPa | mean - k SD |",
          f"| wet XY / Z | in 0.8 | {b['wet']['xy']} / {b['wet']['z']} | Bambu dry/wet bending 125/115, 61/49; 12-18 % decline |",
          f"| hot 40 C | in 0.8 | {b['hot']['chosen']} | Ciganas 2026 PA12 CF15 UTS 40/23 C {b['hot']['direct_40_23_dry']}; Tg-shift readings "
          f"{b['hot']['PA66 (Wetzel 2023, DSC)']['ratio']} / {b['hot']['ForTii PPA (Envalior)']['ratio']} |",
          f"| combined knock-down XY / Z | 0.8 / 0.8 | {b['knock_xy']} / {b['knock_z']} | wet x hot |",
          f"| knocked XY | {b['rec']['xy']} | **{b['hw']['xy']}** MPa (x {b['scale']['xy']}) | |",
          f"| knocked Z | {b['rec']['z']} | **{b['hw']['z']}** MPa (x {b['scale']['z']}) | |",
          f"| interlayer shear | 0.6 x Z = {b['rec']['tau']} | **Z / sqrt 3 = {b['hw']['tau']}** MPa (x {b['scale']['tau']}) | von Mises; 0.6 had no source |",
          f"| modulus 40 C wet | 0.6 (booked) | {b['E_hot_cited']} (0.716 x 0.82) | Ciganas E 40/23 C; ASSUMPTION E-WET |",
          "| Tg | 45 C (ASSUMPTION) | **70 C** dry (DSC), wet 47-58 C | TDS V3.0; record fixed |", "",
          "Record fixed: `data/materials/polymers/pa12_cf_fdm_paht.yaml` glass_transition_c 45 -> 70, glass_transition_wet_c 47, "
          "and the hot/wet B-basis fields with their sources. The V2.0 bending / elongation values the legacy studies read "
          "are left in place (TDS V3.0 is lower; no H1 row uses them: open item).", ""]
    L += ["## 2. Every row, before and after", "",
          f"| row | goal | before (H1, record basis) | H1, hot/wet | **after (H1c {f}, hot/wet)** |", "|---|---:|---:|---:|---:|"]
    for r in rec["rows"]:
        a = f"**{r['after']:.3f}**" + ("" if r["pass_after"] else (" GATED" if r.get("gated_by") else " FAIL"))
        h = f"{r['h1_hw']:.3f}" + ("" if r["pass_h1_hw"] else " FAIL")
        L.append(f"| {r['name']} | {r['goal']:g} | {r['before']:.3f} | {h} | {a} |")
    L += ["", "Hip rows: before / H1 = 8 brass inserts (HB-6 basis scaled to the hot/wet Z); after = sleeved through-bolts "
          "(section 4). Buckling, eigen: H1 bl065 1.336 scaled by the cited modulus "
          f"({e_scale():.3f}); H1c {'re-solved on the export raster at E 1586 MPa (3860 x 0.587 x 0.7, BL-065 rule, crown held, fine_sm8; lead: stay top L; members unbraced >= 4.41; the set-down sets with the crown held but the foot free read 1.20, stay lower L, the BL-065 set-down rule holds the foot as well)' if rec['eigen']['final_solved'] else 'not re-solved: the H1 value is kept (grown body, conservative), the record rule on the export rose'}. "
          f"Clevis: the share-1.0 rows are the extreme; the design share is 0.6 (gate share <= {rec['clevis_share_max']:.2f}).", "",
          "Re-tune steps (exported, re-rastered, 4 bases):", "", "| step | body g | strength | static fat | R1 | creep | joint str | joint fat |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    L.append(f"| H1 | {rec['mass']['H1']['body']:.1f} | {rmap['strength']['h1_hw']:.3f} | {rmap['static_fatigue']['h1_hw']:.3f} | "
             f"{rmap['R1']['h1_hw']:.3f} | {rmap['creep']['h1_hw']:.3f} | {rmap['joint_strength']['h1_hw']:.3f} | {rmap['joint_fatigue']['h1_hw']:.3f} |")
    for s, v in rec["steps"].items():
        L.append(f"| {s} | {v['body_g']} | {v['strength']:.3f} | {v['static_fatigue']:.3f} | {v['R1']:.3f} | {v['creep']:.3f} | "
                 f"{v['joint_strength']:.3f} | {v['joint_fatigue']:.3f} |")
    L += ["", "## 2b. Still below goal on H1c, and the cheapest option for each", ""]
    if not rec["open_rows"]:
        L.append("None.")
    for o in rec["open_rows"]:
        L.append(f"- **{o['row']}: {o['value']} (goal {o['goal']:g}).** {o['why']}.")
        L += [f"  - {x}" for x in o["options"]]
    L += ["", "## 3. Candidates (task 2), scored Strong, then cost, then mass", "",
          "| id | candidate | Strong | verdict |", "|---|---|---|---|"]
    for cd in rec["candidates"]:
        L.append(f"| {cd['id']} | {cd['name']} | {cd['strong']} | {cd['verdict']} |")
    db = rec["candidates"][0]["bound"]
    L += ["", "Perfect-local bound (hot-spot regions taken out of the utilisation population, H1 on the hot/wet basis):", "",
          "| row | all | without lumbar + hip boss | without lumbar + hip boss + stay sleeve z 160-240 |", "|---|---:|---:|---:|"]
    for k, v in db.items():
        L.append(f"| {k} | {v['all']} | {v['lumbar + hip boss']} | {v['lumbar + hip boss + stay sleeve z 160-240']} |")
    L += ["", f"Voxels over 1.0 on the R1 field by region: {db['R1']['voxels_over_1_by_region']}.", ""]
    hp = rec["hip"]
    L += ["## 4. Hip mount", "", "| option | strength | fatigue | creep | verdict |", "|---|---:|---:|---:|---|",
          f"| 8 brass inserts (H1) | {hp['inserts']['min_sf']['strength']} | {hp['inserts']['min_sf']['fatigue']} | "
          f"{hp['inserts']['min_sf']['creep']} | FAIL (pull-out across the layers) |"]
    for tq, v in hp["plates"].items():
        bm = v["bearing_min"]
        L.append(f"| through-bolts + BL-076 arc plates, {tq} N m | {bm['strength']} | {bm['fatigue']} | {bm['creep']} | "
                 f"{'pass' if v['pass'] else 'FAIL'} (plate bending {v['bending_sf']}) |")
    sl = hp["sleeves"]
    L += [f"| **through-bolts + arc plates + 304 sleeves, {sl['torque_nm']} N m** | **{sl['min_sf']['strength']}** | "
          f"**{sl['min_sf']['fatigue']}** | **{sl['min_sf']['creep']}** | adopted |", "",
          f"Plates alone: no torque window (creep needs <= {hp['plates_window']['creep_needs_torque_max_nm']} N m, closure "
          f"(CLOSE-1.3) needs >= {hp['plates_window']['closure_needs_torque_min_nm']} N m; the PAHT path's driver starts at "
          f"0.5). With sleeves the preload ({sl['preload_max_n']:.0f} N max at K 0.14) sits on the steel: sleeve yield SF "
          f"{sl['sleeve_yield_sf']} (annealed 304, {sl['sleeve_area_mm2']} mm2); the PAHT sees only the tipping tension "
          f"(peak {sl['pc_mpa_per_n'] * 1000:.1f} kPa per N, BL-076 plate FE, cold foundation). Sleeves add "
          f"{sl['sleeve_mass_g']} g. Web between sleeve holes D{SLEEVE['hole_d']}: {sl['web_between_holes_mm']} mm "
          "(review-8 rule 3 mm: open item; a 6-bolt pattern would clear it but needs a new mount).", ""]
    L += ["## 5. Sensitivity (one worse assumption at a time, H1c)", "",
          "| variation | settled by | R1 | static fat | joint fat | strength | lug fat | buckling |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for t in rec["tornado"]:
        q = t["rows"]
        L.append(f"| {t['variation']} | {t['retired_by']} | {q['R1']:.2f} | {q['static_fatigue']:.2f} | {q['joint_fatigue']:.2f} | "
                 f"{q['strength']:.2f} | {q['lug_fatigue']:.2f} | {q['buckling']:.2f} |")
    L += ["", "## 6. Coupons (task 3)", "", "| id | what | n | grams | pass line |", "|---|---|---|---:|---|"]
    for cp in rec["coupons"]:
        L.append(f"| {cp['id']} | {cp['what']} | {cp['n']} | {cp['grams']:.0f} | {cp['pass']} |")
    cc = rec["coupon_cost"]
    L += ["", f"Coupon filament {cc['grams']:.0f} g = USD {cc['filament_usd']:.2f}; new items USD {cc['new_items_usd']:.2f} "
          f"({', '.join(n[0] for n in cc['new_items'])}); reused from the kit: {cc['kit_reused']}. **Proving prints USD "
          f"{cc['usd']:.2f} (cap 150).** CA-1-PAHT governing shear Smax {rec['coupons'][1]['smax_test_mpa']} MPa at the test, "
          f"peak {rec['coupons'][1]['peak_load_n']:.0f} N on the SBS jig (under the 100 kg cell). Layer time target "
          f"{rec['layer_time_median_s']:.0f} s.", ""]
    L += ["## 7. Cost (RUBRIC 1b)", "", "| line | H1 (Ti) | H1c (Ti) | H1c (A2) |", "|---|---:|---:|---:|",
          f"| PAHT filament (halves x {SUPPORT_EST_K:.3f} BL-053 support estimate, clevises x 1.08, pawl) | "
          + " | ".join(f"{c[k]['filament']['filament_g']:.0f} g = {c[k]['filament']['usd']:.2f}" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |",
          "| frame hardware | " + " | ".join(f"{c[k]['hardware_usd']:.2f}" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |",
          "| threadlocker share | " + " | ".join(f"{c[k]['threadlocker_share_usd']:.2f}" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |",
          "| **per frame** | " + " | ".join(f"**{c[k]['per_frame_usd']:.2f}**" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |",
          "| per frame, support high bound (x 1.190) | " + " | ".join(f"{c[k]['per_frame_high_usd']:.2f}" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |",
          "| within USD 150 | " + " | ".join("yes" if c[k]["within_cap"] else "**no**" for k in ("H1_ti", "H1c_ti", "H1c_a2")) + " |", "",
          f"A2 screws weigh {c['a2_mass_penalty_g']['H1c']:.1f} g more than Ti on H1c (16 screws). At the cheapest hardware the cap "
          f"leaves filament for {c['cap_body_halves_max_g']:.0f} g of halves.", "",
          "H1c (A2) hardware lines:", "", "| item | qty | unit USD | USD | source |", "|---|---:|---:|---:|---|"]
    for h in c["H1c_a2"]["hardware"]:
        L.append(f"| {h['item']} | {h['qty']} | {h['unit_usd']:.2f} | {h['usd']:.2f} | {h['source']} |")
    ff = c["first_frame"]
    L += ["", f"First frame ({ff['variant']}, the cheaper one-off: A2 screws come in 50-packs):", "", "| line | USD |", "|---|---:|",
          f"| {ff['spools_1kg']} x 1 kg PAHT-CF spools (frame + coupons {ff['filament_g_frame_plus_coupons']:.0f} g) | {ff['spools_usd']:.2f} |",
          f"| hardware (laser order at the USD 29 minimum: 4 plates, one spare set) | {ff['hardware_usd']:.2f} |",
          f"| threadlocker bottle | {ff['threadlocker_usd']:.2f} |",
          f"| coupon items (jig pins, salt) | {cc['new_items_usd']:.2f} |",
          f"| new tools ({', '.join(t[0] for t in ff['tools'])}) | {ff['new_tools_usd']:.2f} |",
          f"| **all-in, first frame** | **{ff['all_in_usd'] + cc['new_items_usd']:.2f}** |", "",
          "Outside the cap scope (carry over unchanged): crown tubes, rack, clamp, pawl pin, Ti / 7075 pins, bushings, "
          "the SLM Ti hip mount (ASSUMPTION COST-SCOPE).", ""]
    ms = rec["mass"]
    L += ["## 8. Mass of every load-path member", "", "| member | H1 g | H1c g |", "|---|---:|---:|"]
    for k in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R", "body"):
        L.append(f"| {k} | {ms['H1'][k]:.1f} | {ms[f][k]:.1f} |")
    hh = ms["hip_hardware_g"]
    L += [f"| hip hardware (inserts + M5 x 12 / M5 x 35 + nuts + plates + sleeves) | {hh['H1']:.1f} | {hh['H1c']:.1f} |",
          f"| **frame delta (body + hip hardware)** | | **{ms['frame_delta_g']:+.1f}** |", "",
          "Mass reductions that keep every row: none found in this ticket; the re-tune already thins where the hot/wet "
          "utilisation is below 0.3 (5 cm3 came off). The cost lever runs the other way: A2 screws instead of Ti save "
          f"USD {c['H1c_ti']['per_frame_usd'] - c['H1c_a2']['per_frame_usd']:.2f} a frame for "
          f"+{c['a2_mass_penalty_g']['H1c']:.1f} g. Heavier but not cheaper: H1c is {ms['frame_delta_g']:+.0f} g on H1 "
          "(RUBRIC 2 loses; Strong first).", ""]
    L += ["## 9. Assumptions", ""] + [f"- ASSUMPTION {a['id']}: {a['text']} Settled by: {a['settled_by']}."
                                       for a in rec["assumptions"]] + [""]
    L += ["## 10. What the build pack and kit generators need (not edited: ticket scope)", ""] + \
         [f"- {k}" for k in rec["kit_needs"]] + [""]
    L += ["## 11. Files", "", "- `huntkit/gendesign/bl077_paht.py`, `tests/test_bl077_paht.py`",
          f"- STLs `{rec['stl_dir']}/` (md5 in bl077.json)", "- record fix `data/materials/polymers/pa12_cf_fdm_paht.yaml`",
          "- screenshots: " + ", ".join(f"`{s}`" for s in rec["screenshots"]), ""]
    return "\n".join(L)


def run_eigen(name: str = FINAL, log=print) -> dict:
    """BL-065 eigen buckling of the exported raster at the cited hot/wet buckling modulus (bl070_h1p.eigen on the
    PAHT basis: E 3860 x 0.587 x 0.7), crown held, fine_sm8 only. Cached OUT/eigen_<name>.json."""
    with paht(MAT):
        P.e_buckle = lambda m=MAT: FI.E_PAHT * basis()["E_hot_cited"] * 0.7
        e = P.eigen(name, raster_of(name), bases=("fine_sm8",), setdown=False, log=log, mat=MAT)
    f = e["fine_sm8"]
    out = {"frame_crown_held": f["frame_crown_held"], "members_unbraced_min": f.get("members_unbraced_min"),
           "frame_lead": f.get("frame_lead"), "E_buckle_mpa": FI.E_PAHT * basis()["E_hot_cited"] * 0.7}
    (OUT / f"eigen_{name}.json").write_text(json.dumps(out, default=float, indent=1))
    return out


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else "report"
    if cmd == "base":
        s0 = FI.baseline_solid()
        for mat in (a[1:] or ["paht_hw"]):
            check("h1", s0, mat=mat, orient=True)
        return 0
    if cmd == "step":
        export_step(a[1], a[2], float(a[3]), float(a[4]), n_thin=int(a[5]) if len(a) > 5 else 1)
        return 0
    if cmd == "eigen":
        run_eigen(a[1] if len(a) > 1 else FINAL)
        return 0
    if cmd == "report":
        report(a[1] if len(a) > 1 else FINAL)
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
