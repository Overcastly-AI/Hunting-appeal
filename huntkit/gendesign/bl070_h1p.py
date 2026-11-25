"""BL-070: H1 on Bambu PPA-CF (owner 2026-11-25, "work with a ppu 3d printed frame"; BL-069 read PPU as PPA-CF).

Two jobs:

1. **H1 on PPA.** The checks BL-069 skipped, on the released H1 print (``h1_assembled.stl``, md5-locked) with the
   PPA-CF allowables of ``data/materials/polymers/ppa_cf_fdm.yaml``: the z 234 joint (``frame_h1.joint_check`` with the
   joint material swapped), the US2 lug submodel (``h1_rev5.lug_check``), the US2 clevis joint (``h1_bedfit``), the
   hip-mount inserts (``h1_closeout.hip_check`` on the HB-6 basis), the BL-068 lash pulls (``bl066_cflite.lash_check``)
   and a real eigen re-solve (``bl065_h1_buckling.run_basis`` with the PPA buckling modulus).
2. **H1-P.** The H1 geometry re-tuned for PPA with every bag / hardware interface frozen: material moved from members
   where the PPA in-plane strength and stiffness leave reserve to where interlayer shear (the PPA weak direction)
   governs. Built from voxel masks on the H1 2 mm grid, exported through the release path
   (``h1_buckling.export_print``: the exact features are re-cut by ``frame_h1.print_mesh``), and checked on the exported
   STL re-rastered (RUBRIC 1; BL-066's lesson: smoothing can erode thin roots).

Material rule: frame_comp_d's FDM layer rule (``frame_topopt.layer_failure_index``): in-plane / (knock s_xy), layer
normal / (knock s_z), interlayer shear / (knock 0.6 s_z), layer normal = frame y for both halves as printed (face
down). ``orientation_study`` re-reads every set with the layer normal along frame x or z per half.

Run: ``python -m huntkit.gendesign.bl070_h1p [base | design | export | check <name> | eigen <name> | report]``.
Record: ``designs/pack_5200/iter1/frame/bl070_h1p.{md,json}``; STLs ``designs/pack_5200/iter1/frame/h1p/``.
Units N, mm, MPa, g.
"""
from __future__ import annotations

import contextlib
import json
import math
import time
from pathlib import Path

import numpy as np

from . import frame_iter1 as FI

REPO = FI.REPO
PACK = FI.PACK
DESIGN = PACK / "iter1" / "frame"
STL_DIR = DESIGN / "h1p"
OUT = REPO / "outputs" / "bl070"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261125_bl070_"
REC_JSON = DESIGN / "bl070_h1p.json"
REC_MD = DESIGN / "bl070_h1p.md"
H = FI.H
BASES = FI.BASES
SPLIT_Z = 234.0

# ================================================================================================ materials
RHO_PAHT = 1.06e-3                       # g/mm3, pa12_cf_fdm_paht record
RHO_PPA = 1.25e-3                        # g/mm3, ppa_cf_fdm record (density_kg_m3 1250)
PAHT_BODY_G = 1069.32                    # h1_assembled.stl in PAHT-CF (bl058.json stl): the mass target


def ppa_record() -> dict:
    """The PPA-CF record values this module uses (data/materials/polymers/ppa_cf_fdm.yaml)."""
    from huntkit.materials import load
    r = load("ppa_cf_fdm")
    g = lambda k: float(r.require(k))   # noqa: E731
    return {"rho": g("density_kg_m3"), "E": g("youngs_modulus_xy_mpa"), "E_z": g("youngs_modulus_z_mpa"),
            "s_xy": g("tensile_strength_xy_mpa"), "s_z": g("tensile_strength_z_mpa"),
            "s_z_design": g("tensile_strength_z_design_mpa"), "knock": g("env_knockdown_ratio"),
            "fat": g("fatigue_1e5_ratio"), "rup": g("creep_rupture_8h_40c_ratio"),
            "E_hot": g("modulus_40c_wet_ratio"), "E_creep": g("creep_modulus_8h_40c_ratio"),
            "E_60": g("modulus_60c_ratio"), "impact_cold": g("impact_minus20c_ratio"),
            "impact_z": g("impact_z_kj_m2"), "elong_z": g("elongation_z_pct"),
            # BL-073 hot/wet basis (review 8 B-2 / M-1 / M-8)
            "s_xy_b": g("tensile_strength_xy_b_basis_mpa"), "s_z_b": g("tensile_strength_z_b_basis_mpa"),
            "knock_hw": g("hot_wet_knockdown_ratio"), "wet": g("wet_knockdown_ratio"), "hot": g("hot_40c_ratio"),
            "E_hot_hw": g("modulus_40c_wet_hw_ratio")}


def materials() -> dict:
    """frame_comp_d-style material dicts. ``ppa_design``: BL-069 design values (TDS XY 168, design Z 45 = 57 - 2.4 SD,
    wet knock 0.73). ``ppa_tds``: TDS mean Z 57 with PAHT's 0.8 knock (BL-069's optimistic bound)."""
    r = ppa_record()
    base = {"rule": "layer", "rho": r["rho"], "E": r["E"], "s_xy": r["s_xy"], "fat": r["fat"], "rup": r["rup"],
            "usd_g": None}
    return {"ppa_design": {**base, "label": "PPA-CF design", "s_z": r["s_z_design"], "knock": r["knock"]},
            "ppa_tds": {**base, "label": "PPA-CF TDS mean", "s_z": r["s_z"], "knock": 0.8},
            # BL-073: B-basis (k 3.4066, n 5) x wet 0.73 x hot 40 C 0.85 on XY, Z and interlayer shear
            "ppa_hw": {**base, "label": "PPA-CF hot/wet B-basis", "s_xy": r["s_xy_b"], "s_z": r["s_z_b"],
                       "knock": r["knock_hw"]}}


def joint_material(mat: str = "ppa_design") -> dict:
    """frame_h1.PAHT-shaped dict for the z 234 joint (contact stiffness uses E x E_hot)."""
    r = ppa_record()
    m = materials()[mat]
    return {"s_xy": m["s_xy"], "s_z": m["s_z"], "knock": m["knock"], "fat": m["fat"], "E": r["E"],
            "E_hot": r["E_hot_hw"] if mat == "ppa_hw" else r["E_hot"]}


def e_buckle(mat: str = "ppa_design") -> float:
    """Buckling modulus on the record rule's footing (E_xy x hot x creep): 11800 x 0.85 x 0.85 = 8526 MPa
    (PAHT-CF: 3860 x 0.6 x 0.7 = 1621). BL-073 ``ppa_hw``: 11800 x 0.5876 (conditioned 0.661 x hot 0.889) x 0.85."""
    r = ppa_record()
    return r["E"] * (r["E_hot_hw"] if mat == "ppa_hw" else r["E_hot"]) * r["E_creep"]


@contextlib.contextmanager
def material(mat: str = "ppa_design"):
    """Swap the whole-body check onto ``mat``: frame_comp_d.MATERIALS entry, frame_h1.MAT (whole-body rule),
    frame_h1.PAHT (z 234 joint), frame_iter1.E_BUCKLE (record buckling rule). ``mat`` 'paht_fdm' = no swap."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    saved = (H1.MAT, dict(H1.PAHT), FI.E_BUCKLE)
    try:
        if mat != "paht_fdm":
            D.MATERIALS[mat] = materials()[mat]
            H1.MAT = mat
            H1.PAHT.clear()
            H1.PAHT.update(joint_material(mat))
            FI.E_BUCKLE = e_buckle(mat)
        yield D.MATERIALS[mat]
    finally:
        H1.MAT = saved[0]
        H1.PAHT.clear()
        H1.PAHT.update(saved[1])
        FI.E_BUCKLE = saved[2]


# ================================================================================================ layer rule per axis
SHEAR_OF = {0: (3, 5), 1: (3, 4), 2: (4, 5)}     # Voigt (xx yy zz xy yz xz): shears touching the layer normal
TIN_OF = {0: 4, 1: 5, 2: 3}                      # the in-plane shear


def layer_terms(S: np.ndarray, axis, m: dict) -> np.ndarray:
    """(4, n) failure-index terms of the layer rule: in-plane (von-Mises-like), layer normal, and the two interlayer
    shears (the lower Voigt index first). ``axis``: int or a per-row int array (layer normal per voxel)."""
    A = np.abs(np.asarray(S, float))
    n = A.shape[0]
    ax = np.broadcast_to(np.asarray(axis), (n,))
    k = m["knock"]
    out = np.zeros((4, n))
    for a in (0, 1, 2):
        sel = ax == a
        if not sel.any():
            continue
        Q = A[sel]
        ip = [d for d in range(3) if d != a]
        s1, s2 = SHEAR_OF[a]
        out[0, sel] = np.sqrt(np.maximum(Q[:, ip[0]], Q[:, ip[1]]) ** 2 + 3 * Q[:, TIN_OF[a]] ** 2) / (k * m["s_xy"])
        out[1, sel] = Q[:, a] / (k * m["s_z"])
        out[2, sel] = Q[:, s1] / (k * 0.6 * m["s_z"])
        out[3, sel] = Q[:, s2] / (k * 0.6 * m["s_z"])
    return out


def fi_layer(S: np.ndarray, axis, m: dict) -> np.ndarray:
    return layer_terms(S, axis, m).max(axis=0)


def margins(f: dict, fi_rows: list, m: dict) -> dict:
    """Body margins as frame_comp_d.evaluate reads them (per scenario tag: strength = 1 / FI99 min over its sets;
    fatigue / creep from the static-carry set with the largest FI99), min over tags. ``fi_rows``: FI per set."""
    per: dict = {}
    for fi, mt in zip(fi_rows, f["meta"]):
        ex = f["ex"][mt["scenario"]]
        fi99 = float(np.percentile(fi[~ex], 99))
        o = per.setdefault(mt["scenario"], {"strength": 9e9, "fi_sc": 0.0, "sc_factor": 1.0})
        o["strength"] = min(o["strength"], 1.0 / max(fi99, 1e-9))
        if mt["case"] == "static_carry" and fi99 > o["fi_sc"]:
            o["fi_sc"], o["sc_factor"], o["sc_set"] = fi99, mt["factor"], mt["set"]
    out = {"strength": 9e9, "fatigue": 9e9, "creep": 9e9}
    for tg, o in per.items():
        out["strength"] = min(out["strength"], o["strength"])
        if o["fi_sc"] > 0:
            out["fatigue"] = min(out["fatigue"], m["fat"] / (o["fi_sc"] * 1.6 / o["sc_factor"]))
            out["creep"] = min(out["creep"], m["rup"] / (o["fi_sc"] / o["sc_factor"]))
    return out


# ================================================================================================ whole-body check
def solve(solid: np.ndarray, basis: str) -> dict:
    """Unit-modulus fields of every set on ``basis`` (lane kit sets, real crown models), stays sanded (k 1.0416)."""
    from . import h1_closeout as C
    from . import h1_sleeve as S
    c = FI._base()
    with FI._ctx():
        b, cyc = basis.split(".")[0], basis.endswith(".cyc")
        sets = S.kit_sets(b, cycled=cyc)
        f = S.solve_fields_w(c["dom"], solid, sets, None)
    stay = C.stay_mask(f["cen"])
    for st in f["stress"]:
        st[stay] *= np.float32(FI.SAND_K)
    return f


def _halves(cen: np.ndarray) -> np.ndarray:
    return np.where(cen[:, 2] < SPLIT_Z, 0, 1)


ORIENT = {"y/y (as printed)": (1, 1), "x/y": (0, 1), "z/y": (2, 1), "y/x": (1, 0), "y/z": (1, 2)}


def check_body(name: str, solid: np.ndarray, bases=BASES, mat: str = "ppa_design", log=print,
               refresh: bool = False, joint: bool = True, orient: bool = False) -> dict:
    """The BL-058 whole-body check (frame_iter1.check rules: FI99 layer rule, 4 bases, sanded stays) on ``solid``
    with ``mat``; adds per voxel the governing layer-rule term of the fatigue utilisation, the joint check on the
    PPA joint material, the record buckling rule at the PPA buckling modulus and (``orient``) the margins with the
    layer normal along frame x / z per half. Cached OUT/check_<name>_<mat>.json, utilisation OUT/util_<name>_<mat>*.npz."""
    from . import frame_h1 as H1
    from . import h1_sleeve as S
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"check_{name}_{mat}.json"
    res = json.loads(p.read_text()) if (p.exists() and not refresh) else {"name": name, "mat": mat}
    todo = [b for b in bases if b not in res]
    if not todo:
        return res
    res["raster_voxels"] = int(solid.sum())
    for b in todo:
        t0 = time.time()
        f = solve(solid, b)
        with material(mat) as m:
            r = S.evaluate(f)
            idx = f["idx"]
            sb = FI.section_buckling(f["cen"], lambda q: q[idx], f["stress"], f["meta"],
                                     np.ones(idx.size, np.float32))
            jc = H1.joint_check(f) if joint else None
            # governing term of the fatigue utilisation per voxel (static-carry sets), and the strength envelope
            n = idx.size
            fat_u = np.zeros(n)
            fat_t = np.zeros(n, np.int8)
            env = np.zeros(n)
            for st, mt in zip(f["stress"], f["meta"]):
                ex = f["ex"][mt["scenario"]]
                T = layer_terms(st, 1, m)
                fi = np.where(ex, 0.0, T.max(axis=0))
                env = np.maximum(env, fi)
                if mt["case"] == "static_carry":
                    u = fi * (1.6 / mt["factor"]) / m["fat"]
                    up = u > fat_u
                    fat_u[up] = u[up]
                    fat_t[up] = T[:, up].argmax(axis=0)
            top = fat_u >= np.percentile(fat_u[fat_u > 0], 99)
            share = {nm: float((fat_t[top] == k).mean()) for k, nm in
                     enumerate(("in_plane", "layer_normal", "shear_xy", "shear_yz"))}
            row = {"min": r["min"], "governing_tag": r["governing_tag"], "per_tag": r["per_tag"],
                   "top_regions": r["top_regions"], "fatigue_top1pct_term_share": share,
                   "buckling_record": sb,
                   "buckling_record_min": min(v["margin_record"] for v in sb.values() if v["margin_record"]),
                   "joint": jc, "joint_strength": float(jc["min_strength"]) if jc else None,
                   "joint_fatigue": float(jc["min_fatigue"]) if jc else None}
            if orient:
                hv = _halves(f["cen"])
                row["orientation"] = {}
                for lab, (alo, ahi) in ORIENT.items():
                    ax = np.where(hv == 0, alo, ahi)
                    rows = [fi_layer(st, ax, m) for st in f["stress"]]
                    row["orientation"][lab] = margins(f, rows, m)
                    del rows
            ut = np.asarray(r["util"], np.float32)
        np.savez_compressed(OUT / f"util_{name}_{mat}_{b}.npz", util=ut, idx=idx, fat_u=fat_u.astype(np.float32),
                            fat_t=fat_t, env=env.astype(np.float32))
        row["seconds"] = round(time.time() - t0)
        res[b] = row
        p.write_text(json.dumps(res, default=FI._jd))
        if log:
            log(f"[{time.strftime('%H:%M:%S')}] {name} {mat} {b}: {json.dumps(r['min'], default=float)} "
                f"buckling rec {row['buckling_record_min']:.2f} joint {row['joint_strength']} / {row['joint_fatigue']} "
                f"shear share {share} ({row['seconds']} s)")
        del f
    return res


def util_field(name: str, mat: str = "ppa_design", bases=BASES, key: str = "util") -> np.ndarray:
    """Max over ``bases`` of a saved per-voxel field on the full grid (0 off the body)."""
    g = FI._base()["dom"].grid
    u = np.zeros(g.ne, np.float32)
    for b in bases:
        z = np.load(OUT / f"util_{name}_{mat}_{b}.npz")
        np.maximum.at(u, z["idx"], z[key].astype(np.float32))
    return u


def summary(res: dict) -> dict | None:
    """Static-cinch = min over fine_sm8 / fine / beam; cinch-cycled = fine_sm8.cyc (BL-058 reading)."""
    if not all(b in res for b in BASES):
        return None
    st = [b for b in BASES if not b.endswith(".cyc")]
    out = {}
    for nm, bs in (("static_cinch", st), ("cinch_cycled", ["fine_sm8.cyc"])):
        o = {k: round(min(res[b]["min"][k] for b in bs), 3) for k in ("strength", "fatigue", "creep")}
        o["buckling_record"] = round(min(res[b]["buckling_record_min"] for b in bs), 3)
        js = [res[b]["joint_strength"] for b in bs if res[b].get("joint_strength") is not None]
        jf = [res[b]["joint_fatigue"] for b in bs if res[b].get("joint_fatigue") is not None]
        o["joint_strength"] = round(min(js), 3) if js else None
        o["joint_fatigue"] = round(min(jf), 3) if jf else None
        out[nm] = o
    return out


# ================================================================================================ H1-P geometry
# Rules (ASSUMPTION H1P-RULES): material moves only on the voxel model of the released print, on the H1 2 mm grid.
# - Frozen: every interface voxel (frame_iter1.protected: pads, fairlead field, hip boss + insert pilots, pawl
#   housing, spine-channel ring, z 234 joint bosses / holes, stay feet z < 40, lug blocks |x| > 125, each dilated
#   6 mm), the crown sleeves / bores / pawl / pivot / spine channel (frame_comp_d keep mask), team A's member floors
#   (printed radius >= 5 mm on branches, struts, mid bar; foot ball 8.4 mm), the lash points (bl068_lash_loads.json,
#   12 mm round each) and the wearer face (the plate face as printed: no voxel with an empty -y neighbour is taken,
#   no voxel is added below the body).
# - Thin: surface voxels (an empty +-x, +-z or +y neighbour) where the PPA utilisation, max-filtered over 6 mm, is
#   below ``u_lo``, if the member stays >= MIN_DEPTH thick there.
# - Grow: empty voxels next to the body (in +-x, +-z, +y) where the utilisation, max-filtered over 4 mm, is above
#   ``u_hi``, inside the design domain, out of the passive voids, the bores and the joint holes.
MIN_DEPTH = 4.0            # mm: EDT depth (centre to the nearest empty voxel) a thinned member keeps at its core
LASH_KEEP_R = 12.0
DIRS = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0))     # grid axes = frame x, y, z; no -y


def _shift(a: np.ndarray, d) -> np.ndarray:
    """a moved by d voxels (out-of-range = False): out[i] = a[i - d]."""
    out = np.zeros_like(a)
    src = tuple(slice(max(-k, 0), a.shape[j] - max(k, 0)) for j, k in enumerate(d))
    dst = tuple(slice(max(k, 0), a.shape[j] - max(-k, 0)) for j, k in enumerate(d))
    out[dst] = a[src]
    return out


def lash_mask(cen: np.ndarray) -> np.ndarray:
    d = json.loads((PACK / "analysis" / "bl068_lash_loads.json").read_text())
    m = np.zeros(len(cen), bool)
    for st in ("after", "before"):
        for row in d[st].values():
            m |= np.linalg.norm(cen - np.asarray(row["point_xyz_mm"], float), axis=1) < LASH_KEEP_R
    return m


def frozen(solid: np.ndarray) -> np.ndarray:
    """Voxels H1-P may never take away (see the rules above)."""
    from . import frame_comp_d as D
    c = FI._base()
    dom, g = c["dom"], c["dom"].grid
    m = FI.protected(solid) | D._keep_mask(dom) | c["floor"] | c["holes"] | lash_mask(c["cen"])
    m |= np.asarray(dom.passive_solid, bool)
    fm = OUT / "feature_mask.npz"
    if fm.exists():           # exact export features (US1 lug-fix hulls, D50 hip boss, ...): voxels taken off the
        m |= np.load(fm)["mask"]   # voxel model inside them come back in the export (c3 trial), so they are frozen
    S = g.to_array(solid)
    wear = S & ~_shift(S, (0, 1, 0))           # the voxel below (-y) is empty: wearer / plate face
    return (m | g.from_array(wear)) & solid


def allowed_add() -> np.ndarray:
    from . import frame_comp_d as D  # noqa: F401
    c = FI._base()
    dom = c["dom"]
    ok = dom.design() & ~np.asarray(dom.passive_void, bool) & ~c["holes"]
    for k, v in dom.masks.items():
        if k.startswith("bore_") or k == "spine_channel":
            ok &= ~np.asarray(v, bool)
    return ok


def resize_step(solid: np.ndarray, util: np.ndarray, u_lo: float, u_hi: float, grow: bool = True,
                thin: bool = True, keep: np.ndarray | None = None) -> tuple:
    """One thin + grow step on the voxel body. ``util`` (g.ne): the PPA utilisation (1 = at the allowable).
    Returns (new solid, removed mask, added mask)."""
    from scipy import ndimage
    c = FI._base()
    g = c["dom"].grid
    S = g.to_array(solid)
    U = g.to_array(np.where(solid, util, 0.0).astype(np.float32))
    rem = np.zeros(g.ne, bool)
    add = np.zeros(g.ne, bool)
    if thin:
        Us = ndimage.maximum_filter(U, size=7)                 # 6 mm neighbourhood (3 voxels)
        surf = np.zeros_like(S)
        for d in DIRS:
            surf |= S & ~_shift(S, tuple(-k for k in d))     # neighbour in direction d is empty
        dep = ndimage.distance_transform_edt(S) * g.h
        core = ndimage.maximum_filter(dep, size=5)             # the member's core depth near the voxel
        cand = surf & (Us < u_lo) & (core >= MIN_DEPTH + g.h)
        rem = g.from_array(cand) & ~frozen(solid)
        if keep is not None:
            rem &= ~keep
    if grow:
        Ug = ndimage.maximum_filter(U, size=5)
        hot = S & (Ug > u_hi)
        nb = np.zeros_like(S)
        for d in DIRS:
            nb |= _shift(hot, d)
        add = g.from_array(nb & ~S) & allowed_add()
    new = (solid & ~rem) | add
    new = FI._connected(new)
    return new, rem & ~new, add & new

@contextlib.contextmanager
def lug_material(mat: str = "ppa_design"):
    """bag_attach._paht (the lug / fairlead submodel material) swapped to ``mat``."""
    from . import bag_attach as BA
    orig = BA._paht
    m = materials()[mat]
    r = ppa_record()
    BA._paht = lambda: {"s_xy": m["s_xy"], "s_z": m["s_z"], "knock": m["knock"], "fat": m["fat"],  # noqa: E731
                        "rupture": m["rup"], "E": r["E"], "rho": r["rho"], "price": 0.20}
    try:
        yield
    finally:
        BA._paht = orig


def us2_lug(mesh=None, mat: str = "ppa_design", tag: str = "h1") -> dict:
    """h1_rev5.lug_check('us2') on the print with ``mat`` (cached OUT/lug_us2_<tag>_<mat>.json)."""
    from . import bl058_frame as BF
    from . import h1_rev5 as R5
    p = OUT / f"lug_us2_{tag}_{mat}.json"
    if p.exists():
        return json.loads(p.read_text())
    with lug_material(mat):
        r = R5.lug_check("us2", mesh=mesh if mesh is not None else BF._mesh(), tag=f"bl070_{tag}")
    r.pop("_field", None)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(r, default=float))
    return r


def us2_clevis(mat: str = "ppa_design") -> dict:
    """US2 clevis joint (BL-056 blocks: clevis_bl056.joint_rows) with the joint material swapped; the strap wrap is
    the BL-056 cached one (geometry unchanged in H1-P: the clevis and its blocks are frozen interfaces)."""
    from . import clevis_bl056 as CB
    wrap = json.loads((REPO / "outputs" / "bl056" / "wrap.json").read_text())
    with material(mat):
        j = CB.joint_rows(wrap)
    out = {}
    for sh in ("share_0.6", "share_1"):
        out[sh] = {"all_rows_min": j[sh]["all_rows_min"], "worst_strength": j[sh]["worst_strength"],
                   "worst_fatigue": j[sh]["worst_fatigue"], "capacities_n": j[sh]["capacities_n"]}
    return out


NUT_SEAT_DEPTH = 13.0      # H1-P hip boss: hex nut seat 13 mm behind the mount face (M5 x 20 DIN 7984 + 3 mm flange)
NUT_WASHER_OD = 6.9        # BL-073 (review 8 B-1): the 8.12 AF hex trap cannot hold a D10 washer, so the BL-070 seat sees
#                            only the nut's own bearing face, dw min 6.9 mm (ISO 4032 / DIN 934 M5): 13.6 mm2. Was 10.0.
#                            The BL-070 through-bolt row therefore FAILS fatigue (1.06 < 1.15 on the BL-069 basis); H1-P
#                            now uses the BL-073 bearing ring (bl073_hotwet.hip_plate), no traps.
NUT_HOLE_D = 5.5


def hip_inserts(mat: str = "ppa_design") -> dict:
    """The BL-055 8-insert hip pattern (HIP_CHOSEN on the D50 boss, h1_closeout.hip_check, HB-6 basis) on PPA, two
    readings of the insert capacity along the layer normal:
    - ``record_rule`` (INS-Z as written): 1200 N x hot knock x host Z / XY TDS ratio (PPA 57 / 168 = 0.339);
    - ``abs_z`` (JOINT-Z): the PAHT HB-6 basis scaled by the knocked Z, 1200 x (knock x Z) / 88 MPa
      (PAHT: 1200 x 0.8 x 47 / 88 = 513 N, the HB-6 pass line).
    And the H1-P fix that keeps the Ti mount and its 8 screw positions: M5 through-bolts with hex nuts in traps on
    the boss's back face (``through_bolt``): the screw load bears on the layers in compression, no pull-out row."""
    from . import h1_closeout as C
    r = ppa_record()
    m = materials()[mat] if mat != "paht_fdm" else None
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    orig = C.insert_record
    ir0 = orig()
    out = {"pattern": {k: pat[k] for k in ("n", "ring_r", "boss_d", "positions_xz")}}
    if m is None:
        out["paht"] = C.hip_check(pat, True)
        return out
    try:
        for key, hot, zr in (("record_rule", m["knock"], r["s_z"] / r["s_xy"]),
                             ("abs_z", 1.0, m["knock"] * m["s_z"] / 88.0)):
            C.insert_record = (lambda hot=hot, zr=zr: {**ir0, "hot": hot, "z_ratio": zr, "fat_ratio": m["fat"],
                                                       "creep_ratio": m["rup"]})
            hc = C.hip_check(pat, True)
            out[key] = {"capacity": hc["capacity"], "min_sf": hc["min_sf"], "pass": hc["pass"]}
            if key == "abs_z":
                rows = hc["rows"]
    finally:
        C.insert_record = orig
    # pass line for the 8-insert pattern on PPA (fatigue row governs: 1.15 x T_walk / fat ratio)
    walk = max(v["T_max_n"] for v in rows.values() if v["kind"] == "fatigue")
    out["hb6_ppa_min_static_n"] = round(C.FAT_GOAL * walk / m["fat"], 1)
    out["hb6_ppa_min_static_basis"] = f"fatigue goal {C.FAT_GOAL} x T_walk {walk:.1f} N / fatigue ratio {m['fat']}"
    # through-bolt option
    from . import frame_h1 as H1
    ring = math.pi / 4 * (NUT_WASHER_OD ** 2 - NUT_HOLE_D ** 2)
    bear = ring * m["knock"] * m["s_z"]
    ti_t, ti_f = 0.7 * H1.TI["uts"] * H1.TI["As"], 0.25 * H1.TI["uts"] * H1.TI["As"]
    tb = {}
    for k, v in rows.items():
        T = v["T_max_n"]
        if v["kind"] == "strength":
            sf = min(bear, ti_t) / T
        elif v["kind"] == "fatigue":
            sf = min(bear * m["fat"], ti_f) / T
        else:
            sf = bear * m["rup"] / T
        tb[k] = {"T_max_n": T, "kind": v["kind"], "sf": round(sf, 2), "goal": v["goal"]}
    gov = {kd: min(r_["sf"] for r_ in tb.values() if r_["kind"] == kd) for kd in ("strength", "fatigue", "creep")}
    out["through_bolt"] = {"nut_seat_depth_mm": NUT_SEAT_DEPTH, "bearing_ring_mm2": round(ring, 1),
                           "bearing_n": round(bear, 1), "rows": tb, "min_sf": gov,
                           "pass": all(r_["sf"] >= r_["goal"] for r_ in tb.values()),
                           "hardware": "8 x Ti gr5 M5 x 20 DIN 7984 + 8 x A2 M5 DIN 934 nuts (Loctite 243) replace "
                                       "8 x M5 x 9.5 brass inserts + 8 x M5 x 12"}
    return out


def lash(solid: np.ndarray, mat: str = "ppa_design", tag: str = "h1") -> dict:
    """BL-068 levelled lash pulls (bl066_cflite.lash_check) with ``mat``."""
    from . import bl066_cflite as L
    p = OUT / f"lash_{tag}_{mat}.json"
    if p.exists():
        return json.loads(p.read_text())
    with material(mat):
        r = L.lash_check(solid=solid, tag=tag, log=lambda *a: None)
    p.write_text(json.dumps(r, default=float))
    return r


def interfaces(mat: str = "ppa_design") -> dict:
    """Interface checks on H1 with ``mat`` that do not depend on the H1-P body edits (clevis, inserts)."""
    return {"us2_clevis": us2_clevis(mat), "hip_inserts": hip_inserts(mat)}


LOOP_BASES = ("fine_sm8", "beam", "fine_sm8.cyc")   # the design loop (fine tracks fine_sm8 within 1 %: BL-058)


def body_g_ppa(solid: np.ndarray) -> float:
    """PPA-CF body mass of a voxel body as BL-061 books concepts: the released STL (1069.32 g PAHT) x rho ratio, plus
    the raster voxel delta against the released print's raster (so the raster / STL difference cancels)."""
    s0 = FI.baseline_solid()
    return PAHT_BODY_G * RHO_PPA / RHO_PAHT + (float(solid.sum()) - float(s0.sum())) * H ** 3 * RHO_PPA


def design_step(prev: str, it_name: str, u_lo: float, u_hi: float, log=print, grow: bool = True,
                thin: bool = True, n_thin: int = 1) -> dict:
    """Resize ``prev`` (a checked body: OUT/<prev>_solid.npz, util files) into ``it_name`` and check it on
    LOOP_BASES. Body saved as OUT/<it_name>_solid.npz."""
    prev_solid = FI.baseline_solid() if prev == "h1" else np.load(OUT / f"{prev}_solid.npz")["solid"]
    u = util_field(prev, "ppa_design", LOOP_BASES)
    new, rem, add = resize_step(prev_solid, u, u_lo, u_hi, grow=grow, thin=thin)
    for _ in range(n_thin - 1):            # more layers off the same low-utilisation field
        new, r2, _a = resize_step(new, u, u_lo, u_hi, grow=False, thin=True, keep=add)
        rem |= r2
    np.savez_compressed(OUT / f"{it_name}_solid.npz", solid=new)
    res = check_body(it_name, new, bases=LOOP_BASES, log=log)
    res["step"] = {"prev": prev, "u_lo": u_lo, "u_hi": u_hi, "grow": grow, "n_thin": n_thin if thin else 0,
                   "removed": int(rem.sum()), "added": int(add.sum()),
                   "body_g_ppa": round(body_g_ppa(new), 1)}
    (OUT / f"check_{it_name}_ppa_design.json").write_text(json.dumps(res, default=FI._jd))
    if log:
        log(f"  {it_name}: -{int(rem.sum())} +{int(add.sum())} voxels, body {res['step']['body_g_ppa']} g, "
            f"cyc fatigue {res['fine_sm8.cyc']['min']['fatigue']:.3f}")
    return res


# ================================================================================================ eigen buckling
def eigen(name: str, solid: np.ndarray, bases=("fine_sm8", "fine_sm8.cyc"), setdown: bool = True,
          log=print, mat: str = "ppa_design") -> dict:
    """BL-065 linear eigen buckling (bl065_h1_buckling.run_basis: crown held, member isolation, Rayleigh screen,
    record model free; run_setdown: foot on the ground) at the PPA buckling modulus (``e_buckle``: 8526 MPa, the
    record rule's footing E_xy x hot x creep). Isotropic voxels at E_xy (ASSUMPTION E-ISO: the members buckle in
    bending along their own axis, an in-plane direction; the layer-normal modulus 4300 MPa is reported as a bound,
    margin x E_z / E_xy). Cached OUT/eigen/<name>_<basis>.json."""
    from . import bl065_h1_buckling as B
    saved = (B.E_B, B.OUT)
    out = {}
    try:
        B.E_B = e_buckle(mat)
        B.OUT = OUT / ("eigen" if mat == "ppa_design" else f"eigen_{mat}")
        B.OUT.mkdir(parents=True, exist_ok=True)
        b = B.body()
        for bs in bases:
            r = B.run_basis(bs, b=b, solid=solid, tag=name, log=log)
            # BL-065 frame reading (bl065_report.frame_rows): crown held on every non-set-down set run; set-down
            # sets are read with the foot on the ground (run_setdown) below
            fr = {k: v["modes"][0] for k, v in r["full"].items() if "single_stay_setdown" not in k}
            fk = min(fr, key=lambda k: fr[k]["margin"])
            row = {"frame_crown_held": fr[fk]["margin"], "frame_lead": fr[fk].get("lead"), "frame_set": fk,
                   "setdown_sets_crown_held_foot_free": min((v["modes"][0]["margin"] for k, v in r["full"].items()
                                                              if "single_stay_setdown" in k), default=None),
                   "record_model_free": r["free_min"]["margin"],
                   "members_unbraced_min": min(v["unbraced"]["margin"] for v in r["members"].values()),
                   "members_braced_min": min(v["braced"]["margin"] for v in r["members"].values()),
                   "seconds": r["seconds"]}
            if setdown and bs == bases[0]:
                sd = B.run_setdown(bs, b=b, solid=solid, tag=name, log=log)
                if sd.get("sets"):
                    row["setdown_foot_held_top_free"] = sd["min_foot_held"]
                    row["setdown_foot_and_crown_held"] = sd["min_foot_held_crown_held"]
            out[bs] = row
    finally:
        B.E_B, B.OUT = saved
    r = ppa_record()
    out["E_buckle_mpa"] = round(e_buckle(mat), 1)
    out["layer_normal_bound_factor"] = round(r["E_z"] / r["E"], 3)
    return out


# ================================================================================================ export (H1-P)
def add_hip_through(man, log=print, stats: dict | None = None):
    """H1-P hip boss (replaces h1_closeout.add_hip_pilots in the export): the same D50 boss grown from the wearer
    face, the same 8 positions (HIP_CHOSEN), but M5 clearance holes (D5.5) straight through and a hex nut trap
    (8.0 AF + 0.12, DIN 934 M5) from the back face down to NUT_SEAT_DEPTH behind the mount face. The holes print as
    vertical holes on the plate face and the traps open upward (top of the print): no support."""
    import manifold3d as m3d
    from . import h1_closeout as C
    from . import h1_rev5 as R5
    n, r, D = C.HIP_CHOSEN[:3]
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    cx, cz = C.HIP_C
    probe = man ^ R5._box_m((cx - 10.0, -80.0, cz - 10.0), (cx + 10.0, -20.0, cz + 10.0))
    y_face = float(probe.bounding_box()[1])
    y0 = y_face - 0.05
    v0 = man.volume()
    man = man + C._cyl_y(cx, cz, y0, y_face + C.HIP_BOSS_DEPTH, D)
    v1 = man.volume()
    seat = y0 + NUT_SEAT_DEPTH
    for x, z in pat["positions_xz"]:
        man = man - C._cyl_y(x, z, y0 - 1.0, y0 + 60.0, NUT_HOLE_D, 48)
        hexp = m3d.Manifold.cylinder(60.0, 8.0 / math.sqrt(3) + 0.12, 8.0 / math.sqrt(3) + 0.12, 6)
        man = man - hexp.rotate((-90.0, 0.0, 0.0)).translate((x, seat, z))
    v2 = man.volume()
    st = {"y_face": round(y0, 3), "nut_seat_y": round(seat, 3), "boss_added_mm3": round(v1 - v0, 1),
          "holes_traps_cut_mm3": round(v1 - v2, 1), "pattern": pat["positions_xz"]}
    if stats is not None:
        stats.update(st)
    if log:
        log(f"  H1-P hip boss D{D:g}: {n} through holes D{NUT_HOLE_D} + hex traps, seat {NUT_SEAT_DEPTH} mm deep")
    return man


def voxel_source(h1p_raster: np.ndarray) -> np.ndarray:
    """The release voxel body (h1_buckling.final_solid at CHOSEN) with H1-P's edits applied: the voxels H1-P took
    from the released print's raster removed, the voxels it added added."""
    from . import h1_buckling as B
    s0 = FI.baseline_solid()
    src = B.final_solid(*B.CHOSEN)
    rem = s0 & ~h1p_raster
    add = h1p_raster & ~s0
    return (src | add) & ~rem


def export(h1p_raster: np.ndarray, log=print, hip_through: bool = True) -> dict:
    """H1-P print files through the release path (h1_buckling.export_print: frame_h1.print_mesh re-cuts every exact
    feature, US2 clevis split, halves laid flat and turned on the H2S bed) into STL_DIR; mass booked at PPA density."""
    import shutil
    from . import frame_h1 as H1
    from . import h1_buckling as B
    from . import h1_closeout as C
    STL_DIR.mkdir(parents=True, exist_ok=True)
    src = voxel_source(h1p_raster)
    saved = (H1.PRINT_DIR, B.OUT, B.final_solid, C.add_hip_pilots)
    try:
        H1.PRINT_DIR = STL_DIR
        B.OUT = OUT / "export"
        B.final_solid = lambda *a: src     # noqa: E731
        if hip_through:
            C.add_hip_pilots = add_hip_through
        info = B.export_print(*B.CHOSEN, log=log)
    finally:
        H1.PRINT_DIR, B.OUT, B.final_solid, C.add_hip_pilots = saved
    for f in STL_DIR.glob("*.3mf"):
        f.unlink()                          # STL only for review; 3MF after owner sign-off
    for k in ("assembled", "lower", "upper"):
        if k in info and "volume_cm3" in info[k]:
            info[k]["g_ppa"] = round(info[k]["volume_cm3"] * 1000 * RHO_PPA, 1)
    (OUT / "export_info.json").write_text(json.dumps(info, default=FI._jd, indent=1))
    shutil.copy(OUT / "export" / "print_info.json", OUT / "export_print_info.json") if (OUT / "export" / "print_info.json").exists() else None
    return info


def reraster(path: Path | None = None) -> np.ndarray:
    """The exported H1-P assembled STL re-rastered on the H1 grid (bl058_frame.body_stl's rule)."""
    import trimesh
    from . import bl058_frame as BF
    m = trimesh.load(path or STL_DIR / "h1_assembled.stl", force="mesh")
    solid, info = BF.body_stl(m)
    return solid, info


# ================================================================================================ coupons (register rows)
EMPTY_PACK_KG = 4.04       # RUBRIC: 4038.1 g base mass proven now (weight_rollup_v2, BL-067)
DROP_M = 1.22              # HA-LS-1 T4c: 48 in / 122 cm


def coupons(m_cyc: float, m_static_fat: float, m_strength: float, m_buckle: float, m_joint_f: float) -> list:
    """Register rows (NOT written to the kit / register; the orchestrator adds them) for the PPA-CF allowables H1-P
    rests on. Pass lines tie to H1-P's design-value margins: where interlayer shear governs, a margin M on the design
    knocked Z (0.73 x 45 = 32.85 MPa) means the frame passes as long as the measured knocked Z is >= 32.85 / M
    (ASSUMPTION LINEAR-Z, BL-069)."""
    m = materials()["ppa_design"]
    r = ppa_record()
    zk = m["knock"] * m["s_z"]                             # 32.85
    need_zk = zk / min(m_cyc, m_joint_f)                   # the knocked Z H1-P needs on R1 and the joint
    need_tau = 0.6 * need_zk
    fat_need = m["fat"] / m_cyc
    e_need = r["E_hot"] / m_buckle                         # E(40 C wet) / E(23 C dry) floor from the buckling margin
    drop_j = EMPTY_PACK_KG / 2.0 * 9.81 * DROP_M
    return [
        {"id": "CA-1-PPA", "what": "R 0.1 tension-tension fatigue, PPA-CF printed on the owner's H2S (H1 profile: "
         "0.6 hardened nozzle, 290 C, bed 110 C, chamber 65 C, 100 % infill), conditioned 14 d at 23 C / 50 % RH",
         "coupons": "6 Z-built (load across the layers, the H1-P governing direction) + 6 XY-built, ISO 527-2 1A "
         "shape, plus 3 static of each from the same plate for the batch UTS",
         "load": f"Smax = {fat_need:.3f} x the batch's own conditioned mean UTS, 1e5 cycles at <= 5 Hz, 23 C",
         "pass": f"all 6 Z-built and all 6 XY-built run out to 1e5 cycles at Smax / UTS = {fat_need:.3f} "
                 f"(= fatigue ratio 0.30 / H1-P cinch-cycled margin {m_cyc:.3f})",
         "settles": "FAT-PPA (fatigue_1e5_ratio 0.30)", "margin_tied": f"R1 {m_cyc:.3f}"},
        {"id": "CA-3-PPA", "what": "Z tensile (ISO 527-2 1A, printed standing: load across the layers) and "
         "interlayer shear (short-beam shear, ASTM D2344 4:1 bar printed flat so the mid-plane is a layer "
         "interface), dry (as printed, sealed with desiccant, tested within 24 h) and conditioned (14 d at 23 C / 50 % RH)",
         "coupons": "6 Z tensile + 6 SBS dry; 6 + 6 conditioned; same spool, same H2S profile as the frame",
         "pass": f"(a) conditioned Z tensile mean - 2.4 SD >= {need_zk:.1f} MPa (H1-P needs knocked Z "
                 f"{zk:.2f} / {min(m_cyc, m_joint_f):.3f}); (b) conditioned SBS mean - 2.4 SD >= {need_tau:.1f} "
                 f"MPa (0.6 x (a), ASSUMPTION INTERLAYER-0.6); (c) for the record: dry Z mean >= 45 MPa and "
                 f"conditioned / dry >= 0.73 means the design values hold as booked",
         "settles": "WET-PPA (knock 0.73), design Z 45 MPa, INTERLAYER-0.6",
         "margin_tied": f"R1 {m_cyc:.3f}, z 234 joint fatigue {m_joint_f:.3f}",
         "if_below": f"(review 8 m-4, corrected) with a measured knocked Z_m: R1 = {m_cyc:.3f} x Z_m / {zk:.2f} and "
                     f"z 234 joint fatigue = {m_joint_f:.3f} x Z_m / {zk:.2f}; at 28 MPa they read "
                     f"{m_cyc * 28 / zk:.3f} / {m_joint_f * 28 / zk:.3f}. Below {need_zk:.1f} MPa hold the PPA build "
                     "(superseded by BL-073 CA-3-HW)"},
        {"id": "CA-4-PPA", "what": "3-point bend modulus and strength (ISO 178, XY-built bars 80 x 10 x 4), at 23 C "
         "dry, at 40 C after 14 d at 23 C / 50 % RH ('40 C wet'), and at 60 C dry (truck cab)",
         "coupons": "5 per condition",
         "pass": f"E(40 C wet) / E(23 C dry) >= 0.85 (the booked ratio; the H1-P buckling margin {m_buckle:.2f} "
                 f"alone would allow {e_need:.2f}); E(60 C) / E(23 C) >= 0.75 (record); flexural strength at "
                 f"60 C >= 0.73 x 208 = {0.73 * 208:.0f} MPa",
         "settles": "modulus_40c_wet_ratio 0.85, modulus_60c_ratio 0.75 (E-SCALE)",
         "margin_tied": f"buckling {m_buckle:.2f}, strength {m_strength:.2f}"},
        {"id": "T4c-PPA", "what": "-20 C drop of a printed stay coupon: the H1-P lower stay z 0-240 (R side) cut "
         "from the lower-half file (foot, hinge eye, US1 lug root), printed in PPA-CF with the frame profile, a 2.0 "
         "kg steel slug pinned through the hinge eye (half the empty pack, 4.04 kg)",
         "coupons": "3 PPA-CF + 1 PAHT-CF control; soaked >= 4 h at -20 C, dropped within 60 s of removal",
         "load": f"1.22 m (48 in, HA-LS-1 T4c) onto 19 mm plywood over concrete, foot first, then side-on "
                 f"(about {drop_j:.0f} J each)",
         "pass": "no crack or whitening (10x loupe, dye penetrant on the foot and the eye), tap test clean, and "
                 "the coupon then carries 3-point bend at 1.5 x its C4 set-down stay moment without a crack; any "
                 "Z crack (along a layer) is a fail",
         "settles": "COLD (impact_minus20c_ratio 0.5; Z Charpy 4.3 kJ/m2 vs PAHT 13.3)",
         "margin_tied": "not in the FI check (impact); this is the PPA risk BL-069 flagged"},
    ]


# ================================================================================================ record
GOALS = {"strength": 1.0, "fatigue": 1.0, "creep": 1.0, "buckling": 1.0, "joint": 1.0,
         "lug_strength": 1.5, "lug_fatigue": 1.15, "hip_strength": 1.5, "hip_fatigue": 1.15, "hip_creep": 1.5,
         "lash": 1.0}


def rows(chk: dict, eig: dict | None, lug: dict, clevis: dict, hip: dict, lash_r: dict, hip_key: str) -> list:
    """The HA-LS-1 rev C rows with their goals (RUBRIC 1: every row >= its goal)."""
    sm = summary(chk)
    out = [("strength (min of 3 static bases)", sm["static_cinch"]["strength"], GOALS["strength"],
            "FI99 layer rule, factored rev C sets"),
           ("fatigue, static carry", sm["static_cinch"]["fatigue"], GOALS["fatigue"], "1e5 x 1.6 g, ratio 0.30"),
           ("fatigue, cinch-cycled (R1)", sm["cinch_cycled"]["fatigue"], GOALS["fatigue"], "fine_sm8.cyc"),
           ("creep (static / cinch-cycled, min)", min(sm["static_cinch"]["creep"], sm["cinch_cycled"]["creep"]),
            GOALS["creep"], "8 h 40 C rupture ratio 0.55"),
           ("z 234 joint strength", min(sm["static_cinch"]["joint_strength"], sm["cinch_cycled"]["joint_strength"]),
            GOALS["joint"], "frame_h1.joint_check, PPA joint material"),
           ("z 234 joint fatigue", min(sm["static_cinch"]["joint_fatigue"], sm["cinch_cycled"]["joint_fatigue"]),
            GOALS["joint"], "boss bending + prying, plug shear-out (interlayer)"),
           ("US2 lug strength", lug["design_min"]["strength"], GOALS["lug_strength"], "h1_rev5.lug_check"),
           ("US2 lug fatigue", lug["design_min"]["fatigue"], GOALS["lug_fatigue"], "h1_rev5.lug_check"),
           ("US2 clevis joint strength (share 1.0)", clevis["share_1"]["all_rows_min"]["strength"],
            GOALS["lug_strength"], "clevis_bl056.joint_rows"),
           ("US2 clevis joint fatigue (share 1.0)", clevis["share_1"]["all_rows_min"]["fatigue"],
            GOALS["lug_fatigue"], "clevis_bl056.joint_rows"),
           (f"hip mount strength ({hip_key})", hip[hip_key]["min_sf"]["strength"], GOALS["hip_strength"], "HB-6 basis"),
           (f"hip mount fatigue ({hip_key})", hip[hip_key]["min_sf"]["fatigue"], GOALS["hip_fatigue"], "HB-6 basis"),
           (f"hip mount creep ({hip_key})", hip[hip_key]["min_sf"]["creep"], GOALS["hip_creep"], "HB-6 basis"),
           ("lash pulls W1 / W2 (BL-068, p99)", lash_r["states"]["after"]["margin_p99"], GOALS["lash"],
            "bl066_cflite.lash_check x 2.0")]
    if eig:
        bs = [b for b in eig if isinstance(eig[b], dict)]
        out.append(("buckling, eigen, frame crown held", min(eig[b]["frame_crown_held"] for b in bs),
                    GOALS["buckling"], f"voxel_buckling, E {e_buckle():.0f} MPa, BL-065 supports"))
        sd = [eig[b]["setdown_foot_and_crown_held"] for b in bs if eig[b].get("setdown_foot_and_crown_held")]
        if sd:
            out.append(("buckling, eigen, set-down (foot + crown held)", min(sd), GOALS["buckling"], "run_setdown"))
        out.append(("buckling, eigen, members (stay tops free)", min(eig[b]["members_unbraced_min"] for b in bs),
                    GOALS["buckling"], "member isolation"))
    else:
        out.append(("buckling, record rule", min(sm["static_cinch"]["buckling_record"],
                                                  sm["cinch_cycled"]["buckling_record"]), GOALS["buckling"],
                    "team A Euler rule at E 8526"))
    return [{"name": n, "value": round(float(v), 3), "goal": g, "basis": b, "pass": bool(v >= g)}
            for n, v, g, b in out]


# ================================================================================================ figures
PAHT_H1 = {   # PAHT-CF H1 of record: bl058.json body (sanded STL), bl065.json, lug / clevis / hip / lash records
    "strength (min of 3 static bases)": 1.63, "fatigue, static carry": 1.249, "fatigue, cinch-cycled (R1)": 0.856,
    "creep (static / cinch-cycled, min)": 1.825, "z 234 joint strength": 1.978, "z 234 joint fatigue": 1.05,
    "US2 lug strength": 3.34, "US2 lug fatigue": 1.50, "US2 clevis joint strength (share 1.0)": 3.02,
    "US2 clevis joint fatigue (share 1.0)": 1.36, "hip mount strength": 2.149, "hip mount fatigue": 1.208,
    "hip mount creep": 2.58, "lash pulls W1 / W2 (BL-068, p99)": 4.18, "buckling, eigen, frame crown held": 1.336,
    "buckling, eigen, set-down (foot + crown held)": 4.11, "buckling, eigen, members (stay tops free)": 1.47}


def _key(n: str) -> str:
    return n.split(" (")[0] if n.startswith("hip mount") else n


def plot_margins(rows_ppa: list, rows_p: list, path: Path) -> str:
    """Margin / goal per row: PAHT H1 (record), PPA H1 (same print), PPA H1-P (exported)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = [r["name"] for r in rows_p]
    goal = {r["name"]: r["goal"] for r in rows_p}
    a = {_key(r["name"]): r["value"] for r in rows_ppa}
    b = {_key(r["name"]): r["value"] for r in rows_p}
    fig, ax = plt.subplots(figsize=(8.6, 10.5), dpi=110)
    y = np.arange(len(names))[::-1]
    h = 0.27
    cols = ("#8a8f98", "#2a78d6", "#eb6834")
    for k, (lab, src) in enumerate((("PAHT-CF H1 (record)", PAHT_H1), ("PPA-CF H1 (same print)", a),
                                    ("PPA-CF H1-P (exported)", b))):
        v = [min(src.get(_key(n), np.nan) / goal[n], 3.0) for n in names]
        ax.barh(y + (1 - k) * h, v, h, color=cols[k], label=lab)
        for yy, vv, n in zip(y, v, names):
            raw = src.get(_key(n))
            if raw is not None and np.isfinite(vv):
                ax.text(min(vv, 3.0) + 0.02, yy + (1 - k) * h, f"{raw:.2f}", va="center", fontsize=6.5,
                        color=cols[k])
    ax.axvline(1.0, color="#c0392b", lw=1.4)
    ax.text(1.01, len(names) - 0.4, "goal", color="#c0392b", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{n.replace('(through_bolt)', '(inserts; H1-P through-bolts)')}  (goal {goal[n]:g})"
                        for n in names], fontsize=7.5)
    ax.set_xlabel("margin / goal (bars clipped at 3; labels = margin)", labelpad=2)
    ax.set_xlim(0, 3.35)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.06), ncol=3, fontsize=8)
    ax.set_title("BL-070: HA-LS-1 rows, PAHT H1 vs PPA H1 vs PPA H1-P\n(design values: PPA Z 45 MPa x 0.73, "
                 "fatigue ratio 0.30)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return str(path)


def plot_util(u_h1: np.ndarray, u_p: np.ndarray, solid_h1: np.ndarray, solid_p: np.ndarray, path: Path,
              m_h1: float, m_p: float) -> str:
    """Cinch-cycled fatigue utilisation (max through the depth), front view, H1 on PPA vs H1-P."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cen = FI._base()["cen"]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 8.2), dpi=100)
    for ax, u, sol, t in ((axs[0], u_h1, solid_h1, f"H1 on PPA-CF: R1 {m_h1:.3f}"),
                          (axs[1], u_p, solid_p, f"H1-P on PPA-CF: R1 {m_p:.3f}")):
        sel = sol
        order = np.argsort(u[sel])
        P = cen[sel][order]
        sc = ax.scatter(P[:, 0], P[:, 2], c=np.clip(u[sel][order], 0, 1.2), s=3.2, cmap="turbo", vmin=0, vmax=1.2,
                        marker="s", linewidths=0)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=10)
        ax.set_xlabel("x mm")
        ax.set_ylabel("z mm")
    cb = fig.colorbar(sc, ax=axs, shrink=0.7)
    cb.set_label("fatigue utilisation, cinch-cycled basis (1 = at the allowable)")
    fig.suptitle("BL-070: cinch-cycled fatigue utilisation, front view (wearer side), max through the depth",
                 fontsize=10.5)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def plot_diff(solid_h1: np.ndarray, solid_p: np.ndarray, path: Path, g_h1: float, g_p: float) -> str:
    """Where H1-P differs from H1 (exported rasters): front and side views."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cen = FI._base()["cen"]
    rem, add, both = solid_h1 & ~solid_p, solid_p & ~solid_h1, solid_h1 & solid_p
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 8.2), dpi=100, gridspec_kw={"width_ratios": [3, 1.3]})
    for ax, (i, j, lab) in zip(axs, ((0, 2, "front (x-z)"), (1, 2, "side (y-z), wearer face left"))):
        for m, c, nm, s in ((both, "#bdbdbd", "kept", 2.0), (rem, "#2a78d6", f"taken off ({int(rem.sum())} vox)", 3.0),
                            (add, "#eb6834", f"added ({int(add.sum())} vox)", 3.0)):
            ax.scatter(cen[m, i], cen[m, j], s=s, c=c, marker="s", linewidths=0, label=nm)
        ax.set_aspect("equal")
        ax.set_title(lab, fontsize=10)
    axs[0].legend(loc="upper center", fontsize=8, markerscale=3)
    fig.suptitle(f"BL-070 H1-P vs H1 (exported STLs re-rastered, 2 mm): PPA-CF body {g_h1:.0f} g -> {g_p:.0f} g",
                 fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def render_pair(path: Path, cap: str, sub: str) -> str:
    """Cycles render (frame_h1.render): H1 left, H1-P right (translated 380 mm)."""
    import trimesh
    from . import frame_h1 as H1
    work = OUT / "render"
    work.mkdir(parents=True, exist_ok=True)
    a = trimesh.load(H1.PRINT_DIR / "h1_assembled.stl", force="mesh")
    b = trimesh.load(STL_DIR / "h1_assembled.stl", force="mesh")
    b.apply_translation((380.0, 0, 0))
    a.export(work / "h1.stl")
    b.export(work / "h1p.stl")
    files = [{"path": str(work / "h1.stl"), "mat": "today"}, {"path": str(work / "h1p.stl"), "mat": "printed"}]
    return H1.render(path, files, cap, sub, az=160.0, el=12.0, zoom=1.0, samples=24)


def shrink_png(path: Path, max_bytes: int = 1_400_000) -> None:
    from PIL import Image
    p = Path(path)
    while p.stat().st_size > max_bytes:
        im = Image.open(p)
        im = im.resize((int(im.width * 0.85), int(im.height * 0.85)))
        im.save(p, optimize=True)


def pinch_points(path: Path) -> list:
    """Points of the non-manifold edges (not shared by exactly 2 faces) of an STL, merged within 5 mm."""
    import trimesh
    m = trimesh.load(path, force="mesh")
    u, c = np.unique(m.edges_sorted, axis=0, return_counts=True)
    bad = u[c != 2]
    out = []
    for e in bad:
        q = m.vertices[e].mean(axis=0)
        if all(np.linalg.norm(q - o) > 5.0 for o in out):
            out.append(q)
    return out


def export_step(prev: str, name: str, u_lo: float, u_hi: float, n_thin: int = 1, grow: bool = True,
                log=print, grow_bases=LOOP_BASES) -> dict:
    """One design step in export space: resize the previous EXPORT raster (OUT/<prev>_solid.npz) on its own
    utilisation, export through the release path, re-raster the export (OUT/<name>_solid.npz), check it on every
    basis (check_<name>). The design raster is kept as OUT/<name>_design.npz."""
    import trimesh
    ps = np.load(OUT / f"{prev}_solid.npz")["solid"]
    u = util_field(prev, "ppa_design", LOOP_BASES)
    ug = util_field(prev, "ppa_design", grow_bases)
    d, _r0, add = resize_step(ps, ug, 0.0, u_hi, grow=grow, thin=False)
    d, rem, _a0 = resize_step(d, np.maximum(u, ug), u_lo, 99.0, grow=False, thin=n_thin > 0, keep=add)
    for _ in range(max(n_thin - 1, 0)):
        d, r2, _a = resize_step(d, u, u_lo, u_hi, grow=False, thin=True, keep=add)
        rem |= r2
    fused = []
    for _ in range(4):
        try:
            info = export(d, log=None)
            break
        except RuntimeError as e:          # a pinch (edge shared by 4 faces) between grown surfaces: fuse it
            pts = pinch_points(STL_DIR / "h1_assembled.stl")
            if not pts:
                raise
            cen = FI._base()["cen"]
            for q in pts:
                f = (np.linalg.norm(cen - q, axis=1) < 3.5) & allowed_add()
                d = d | f
                fused.append({"at_mm": [round(float(v), 1) for v in q], "voxels": int(f.sum()), "why": str(e)[-60:]})
    np.savez_compressed(OUT / f"{name}_design.npz", solid=d)
    rr, rinfo = reraster()
    np.savez_compressed(OUT / f"{name}_solid.npz", solid=rr)
    res = check_body(name, rr, bases=BASES, log=log, orient=True)
    m = trimesh.load(STL_DIR / "h1_assembled.stl", force="mesh")
    res["step"] = {"prev": prev, "u_lo": u_lo, "u_hi": u_hi, "grow": grow, "n_thin": n_thin,
                   "grow_bases": list(grow_bases), "pinches_fused": fused, "removed": int(rem.sum()), "added": int(add.sum()), "body_g_ppa": round(m.volume * RHO_PPA, 1),
                   "design_not_in_export": int((d & ~rr).sum()), "export_not_in_design": int((rr & ~d).sum())}
    (OUT / f"check_{name}_ppa_design.json").write_text(json.dumps(res, default=FI._jd))
    if log:
        log(f"  {name}: body {res['step']['body_g_ppa']} g, R1 {res['fine_sm8.cyc']['min']['fatigue']:.3f}")
    return res


# ================================================================================================ printability (H2S)
SPOOL_G = 750.0            # Bambu PPA-CF spool (record supplier_examples)
WASTE = 1.08               # purge / skirt / brim allowance on the filament (frame_h1_build: + 8 % waste)


def flat_contact_mm2(flat_mesh, tol: float = 0.05) -> float:
    """Area of the laid-flat part's faces on the plate (lowest z, facing down)."""
    m = flat_mesh
    z0 = float(m.bounds[0][2])
    on = (m.triangles_center[:, 2] < z0 + tol) & (m.face_normals[:, 2] < -0.99)   # frame_h1_build.live_print_row
    return float(m.area_faces[on].sum())


def printability(assembled, flat: dict) -> dict:
    """Per half on the H2S, wearer face down (layers normal to frame y, as the FE): plate contact (flat STL), support
    (h1_rev5.support_map voxel estimate, 1 mm), filament in PPA-CF (part + support high bound, + 8 % waste) against
    one 0.75 kg spool, print time by the BL-053 rule (volume / 8 mm3/s x 1.08; ASSUMPTION PPA-TIME: PPA-CF prints at
    the PAHT volume rate, TDS < 100 mm/s), H2S bed fit."""
    from . import h1_rev5 as R5
    from .frame_topopt import split_mesh
    lo, hi = split_mesh(assembled, SPLIT_Z)
    out = {}
    for nm, m, zl in (("lower", lo, (-50.0, SPLIT_Z)), ("upper", hi, (SPLIT_Z, 700.0))):
        sm = R5.support_map(m, up=1.0, h=1.0, zlim=zl)
        part_mm3 = float(flat[nm].volume)
        sup_hi_mm3 = sm["support_column_mm3"] * 0.25 + sm["supported_mm2"] * R5.INTERFACE_MM
        sup_est_mm3 = sm["support_column_mm3"] * R5.TREE_FILL + sm["supported_mm2"] * R5.INTERFACE_MM
        t = (part_mm3 + sup_est_mm3) / R5.VOL_RATE / 3600.0 * R5.TIME_OVERHEAD
        fil_hi = (part_mm3 + sup_hi_mm3) * RHO_PPA * WASTE
        ext = sorted(flat[nm].extents)
        out[nm] = {"plate_contact_mm2": round(flat_contact_mm2(flat[nm]), 0),
                   "plate_contact_voxel_mm2": sm["plate_contact_mm2"], "supported_mm2": sm["supported_mm2"],
                   "supported_by_region_mm2": sm["supported_by_region_mm2"],
                   "max_support_column_mm": sm["max_column_mm"],
                   "part_g_ppa": round(part_mm3 * RHO_PPA, 1),
                   "support_g_ppa_est": round(sup_est_mm3 * RHO_PPA, 1),
                   "support_g_ppa_high": round(sup_hi_mm3 * RHO_PPA, 1),
                   "filament_g_high_with_waste": round(fil_hi, 0),
                   "spools": round(fil_hi / SPOOL_G, 2), "needs_spool_swap": bool(fil_hi > SPOOL_G),
                   "print_h_est": round(t, 1), "extents_mm": [round(v, 1) for v in flat[nm].extents],
                   "fits_h2s_340x320x340": bool(ext[-1] <= 340 and ext[-2] <= 320)}
    return out


ASSUMPTIONS = [
    ("PPU=PPA", "'PPU' is Bambu PPA-CF (BL-069).", "owner confirmation"),
    ("WET-PPA", "Design Z 45 MPa (57 - 2.4 SD) x wet knock 0.73 (Raise3D conditioned / Bambu dry).", "CA-3-PPA"),
    ("FAT-PPA", "fatigue_1e5_ratio 0.30 (PA12-CF lower bound), on the layer rule's FI.", "CA-1-PPA"),
    ("INTERLAYER-0.6", "Interlayer shear strength = 0.6 x Z tensile (frame_topopt layer rule, as PAHT).", "CA-3-PPA SBS"),
    ("LINEAR-Z", "Where interlayer shear governs (92 % of the R1 top 1 %), a margin scales with knock x Z.",
     "re-run check_body with the coupon values"),
    ("E-ISO / E-SCALE", "Voxel FE isotropic at E_xy (the stress fields are unit-modulus, so strength checks do not "
     "depend on it); buckling at E_xy x 0.85 hot x 0.85 creep = 8526 MPa. Layer-normal bound x E_z / E_xy = 0.364.",
     "CA-4-PPA (40 C wet, 60 C); T1 deflection at 150 lb"),
    ("JOINT-Z", "z 234 joint and US2 clevis capacities on the PPA joint dict: washer / contact bearing on knock x "
     "XY, plug shear-out and clevis hole bearing on knock x Z; contact stiffness E x 0.85.", "CA-3-PPA"),
    ("INS-PPA", "Insert pull-out on PPA either by the record rule (hot x Z/XY TDS ratio 0.339: 297 N) or by the "
     "PAHT HB-6 basis scaled by knocked Z (448 N); both fail the 8-insert fatigue row (needs 488 N).",
     "HB-6-PPA only if inserts are kept"),
    ("NUT-BEAR", "H1-P hip mount through-bolts: nut / D10 washer bearing on the layers in compression taken at knock "
     "x design Z (32.9 MPa) on the ring D10 / D5.5; tipping model and rigid flange as BL-055 (FLANGE-RIGID).",
     "HB-6b on the frame (hip mount proof) with the through-bolts"),
    ("H1P-RULES", "H1-P moves material only on the 2 mm voxel model of the released print: interfaces, crown "
     "sleeves, member floors, lash points and the wearer (plate) face frozen; thinning one surface layer at a time "
     "where the PPA utilisation (6 mm max filter) is low, growth where it is high.", "the checks on the export"),
    ("PPA-TIME", "Print time by the BL-053 rule (8 mm3/s x 1.08) at the PAHT volume rate; TDS speed < 100 mm/s.",
     "slicer preview"),
    ("WARP", "PPA-CF (E x 3, crystallises at 178 C) warps more than PAHT on a small plate contact; chamber pre-heat "
     "30 min at 65 C, glue, brim 15 mm, mouse ears at the stay feet.", "first article"),
    ("COLD", "impact_minus20c_ratio 0.5; Z Charpy 4.3 kJ/m2.", "T4c-PPA"),
    ("SPOOL-SWAP", "A half that needs > 0.75 kg is started on a full dried spool with a second dried spool staged "
     "(AMS feed of PPA-CF on the H2S not verified).", "first article"),
]


# ================================================================================================ pipeline
FINAL_ITER = "g1"          # lightest export step passing every row (outputs/bl070: c3 export R1 0.987, g1 1.076, f1 1.098)
HIP_KEY = "through_bolt"   # H1-P hip mount: M5 through-bolts + hex nuts (inserts fail fatigue on PPA)


def finalize(final_iter: str = FINAL_ITER, log=print) -> dict:
    """The chosen export step (export_step: exported through the release path, re-rastered, checked on every basis):
    make sure the STLs in STL_DIR are that step's (re-export its design raster if another step overwrote them),
    then the US2 lug submodel on its mesh, the lash pulls on its raster and the printability of its halves."""
    import trimesh
    d = np.load(OUT / f"{final_iter}_design.npz")["solid"]
    rr = np.load(OUT / f"{final_iter}_solid.npz")["solid"]
    rr_now, _ = reraster()
    info = json.loads((OUT / "export_info.json").read_text())
    if not np.array_equal(rr_now, rr):
        info = export(d, log=log)
        rr_now, _ = reraster()
        if not np.array_equal(rr_now, rr):
            raise RuntimeError(f"re-export of {final_iter} does not reproduce its checked raster")
    _, rinfo = reraster()
    res = json.loads((OUT / f"check_{final_iter}_ppa_design.json").read_text())
    m = trimesh.load(STL_DIR / "h1_assembled.stl", force="mesh")
    lug = us2_lug(mesh=m, tag=final_iter)
    la = lash(rr, tag=final_iter)
    fl = {n: trimesh.load(STL_DIR / f"h1_{n}_flat.stl", force="mesh") for n in ("lower", "upper")}
    pr = printability(m, fl)
    out = {"final_iter": final_iter, "check_name": final_iter, "export": info, "reraster": rinfo,
           "check": summary(res), "lug": lug, "lash": la, "print": pr, "body_g": round(m.volume * RHO_PPA, 1),
           "voxels": {"design_raster": int(d.sum()), "exported_raster": int(rr.sum()),
                      "design_not_in_export": int((d & ~rr).sum()), "export_not_in_design": int((rr & ~d).sum())}}
    (OUT / "finalize.json").write_text(json.dumps(out, default=FI._jd, indent=1))
    return out


def run_eigen_h1p(log=print) -> dict:
    fin = json.loads((OUT / "finalize.json").read_text())
    rr = np.load(OUT / f"{fin['final_iter']}_solid.npz")["solid"]
    r = eigen(fin["final_iter"], rr, bases=("fine_sm8", "fine_sm8.cyc"), setdown=True, log=log)
    (OUT / "eigen_h1p.json").write_text(json.dumps(r, default=FI._jd, indent=1))
    return r


def _j(p: Path):
    return json.loads(Path(p).read_text())


def steps() -> list:
    out = []
    for p in sorted(OUT.glob("check_*_ppa_design.json"), key=lambda q: q.stat().st_mtime):
        d = _j(p)
        if "step" not in d or d["name"].startswith("it"):
            continue
        x = {"name": d["name"], **d["step"],
             "geometry": "export re-raster" if "design_not_in_export" in d["step"] else "voxel model",
             "cyc": round(d["fine_sm8.cyc"]["min"]["fatigue"], 3),
             "static_fatigue": round(min(d[b]["min"]["fatigue"] for b in ("fine_sm8", "beam")), 3),
             "strength": round(min(d[b]["min"]["strength"] for b in LOOP_BASES), 3),
             "joint_fatigue": min(d[b]["joint_fatigue"] for b in LOOP_BASES)}
        out.append(x)
    return out


def report(log=print) -> dict:
    """Assemble the record (REC_JSON), the doc (REC_MD) and the screenshots from the cached runs."""
    import trimesh
    ck = _j(OUT / "check_h1_ppa_design.json")
    itf = _j(OUT / "interfaces_h1.json")
    fin = _j(OUT / "finalize.json")
    eig_h1 = eigen("h1", FI.baseline_solid(), bases=("fine_sm8",), setdown=True, log=log)
    eig_p = _j(OUT / "eigen_h1p.json")
    ck_p = _j(OUT / f"check_{fin['check_name']}_ppa_design.json")
    lug_h1 = _j(OUT / "lug_us2_h1_ppa_design.json")
    lash_h1 = _j(OUT / "lash_h1_ppa_design.json")
    hip = itf["ppa_design"]["hip_inserts"]
    clev = itf["ppa_design"]["us2_clevis"]
    r_h1 = rows(ck, eig_h1, lug_h1, clev, hip, lash_h1, "abs_z")
    r_h1_rec = [x for x in rows(ck, eig_h1, lug_h1, clev, hip, lash_h1, "record_rule") if "hip" in x["name"]]
    r_p = rows(ck_p, eig_p, fin["lug"], clev, hip, fin["lash"], HIP_KEY)
    g_h1 = round(PAHT_BODY_G * RHO_PPA / RHO_PAHT, 1)
    g_p = fin["body_g"]
    byn = {x["name"]: x for x in r_p}
    m_cyc = byn["fatigue, cinch-cycled (R1)"]["value"]
    m_jf = byn["z 234 joint fatigue"]["value"]
    m_b = min(x["value"] for x in r_p if x["name"].startswith("buckling"))
    cps = coupons(m_cyc, byn["fatigue, static carry"]["value"], byn["strength (min of 3 static bases)"]["value"],
                  m_b, m_jf)
    pr_h1 = _j(OUT / "print_h1.json")
    # screenshots
    SCREENS.mkdir(parents=True, exist_ok=True)
    s0 = FI.baseline_solid()
    sp = np.load(OUT / f"{fin['final_iter']}_solid.npz")["solid"]
    shots = []
    p1 = SCREENS / f"{SHOT}1.png"
    try:
        render_pair(p1, f"H1 (left, PPA-CF {g_h1:.0f} g) vs H1-P (right, {g_p:.0f} g)",
                    f"same interfaces; R1 {byn['fatigue, cinch-cycled (R1)']['value']:.2f} on PPA design values "
                    f"(H1 on PPA 0.94); PAHT H1 1069 g")
    except Exception as e:                                  # pragma: no cover  (no bpy venv)
        log(f"render failed ({e}); diff figure only")
    if p1.exists():
        shots.append(str(p1))
    p2 = SCREENS / f"{SHOT}2.png"
    shots.append(plot_margins(r_h1, r_p, p2))
    u1 = util_field("h1", "ppa_design", ("fine_sm8.cyc",))
    u2 = util_field(fin["final_iter"], "ppa_design", ("fine_sm8.cyc",))
    p3 = SCREENS / f"{SHOT}3.png"
    shots.append(plot_util(u1, u2, s0, sp, p3, summary(ck)["cinch_cycled"]["fatigue"], m_cyc))
    p4 = SCREENS / f"{SHOT}4.png"
    shots.append(plot_diff(s0, sp, p4, g_h1, g_p))
    for q in shots:
        shrink_png(Path(q))
    rec = {"ticket": "BL-070", "date": "2026-11-25", "material": "data/materials/polymers/ppa_cf_fdm.yaml",
           "materials": materials(), "e_buckle_mpa": round(e_buckle(), 1),
           "h1_paht_record": PAHT_H1,
           "h1_ppa": {"stl": "designs/pack_5200/print/frame_h1/h1_assembled.stl", "stl_md5": FI.STL_MD5,
                      "body_g": g_h1, "summary": summary(ck), "rows": r_h1, "hip_record_rule_rows": r_h1_rec,
                      "fatigue_top1pct_term_share": ck["fine_sm8.cyc"]["fatigue_top1pct_term_share"],
                      "top_regions_cyc": ck["fine_sm8.cyc"]["top_regions"],
                      "orientation": {b: ck[b]["orientation"] for b in BASES},
                      "joint_cyc": ck["fine_sm8.cyc"]["joint"]["fatigue"], "eigen": eig_h1,
                      "us2_clevis": clev, "hip_inserts": hip, "lash": lash_h1["states"]["after"],
                      "print": pr_h1, "paht_control_cyc": _j(OUT / "check_h1_paht_fdm.json")["fine_sm8.cyc"]["min"]},
           "h1p": {"checked_on": "exported STL re-rastered on the H1 2 mm grid (bl058_frame.body_stl rule)",
                   "stl_dir": str(STL_DIR.relative_to(REPO)), "final_iter": fin["final_iter"], "steps": steps(),
                   "body_g": g_p, "delta_vs_paht_h1_g": round(g_p - PAHT_BODY_G, 1),
                   "delta_vs_h1_ppa_g": round(g_p - g_h1, 1), "summary": fin["check"], "rows": r_p,
                   "rows_by_name": byn, "fatigue_top1pct_term_share": ck_p["fine_sm8.cyc"]["fatigue_top1pct_term_share"],
                   "orientation": {b: ck_p[b]["orientation"] for b in BASES}, "eigen": eig_p,
                   "print": fin["print"], "export": fin["export"], "reraster": fin["reraster"],
                   "voxels": fin["voxels"], "hip_mount": hip["through_bolt"]},
           "coupons": cps,
           "assumptions": [{"id": a, "text": t, "settled_by": b} for a, t, b in ASSUMPTIONS],
           "screenshots": [str(Path(q).relative_to(REPO)) for q in shots]}
    REC_JSON.write_text(json.dumps(rec, default=FI._jd, indent=1))
    write_md(json.loads(REC_JSON.read_text()))
    log(f"record {REC_JSON}")
    return rec


def _lb(g: float) -> str:
    return f"{g / 453.6:.2f} lb"


def write_md(rec: dict) -> str:
    """designs/pack_5200/iter1/frame/bl070_h1p.md from the record."""
    h, p = rec["h1_ppa"], rec["h1p"]
    L = ["# BL-070 H1 on PPA-CF, and H1-P (the H1 geometry re-tuned for PPA-CF)", "",
         "Data: `bl070_h1p.json` (written by `python -m huntkit.gendesign.bl070_h1p report`). Code: "
         "`huntkit/gendesign/bl070_h1p.py`. Tests: `tests/test_bl070_h1p.py`. STLs: `h1p/` (review copies, STL only). "
         f"Date {rec['date']}. Units N, mm, MPa, g (imperial in brackets). Material: `{rec['material']}` design "
         "values (XY 168, Z 45 MPa, wet knock 0.73, fatigue ratio 0.30, creep-rupture 0.55); buckling modulus "
         f"{rec['e_buckle_mpa']:.0f} MPa.", "",
         "## HA-LS-1 rows", "",
         "PAHT and PPA H1 columns: BL-069 design basis. **H1-P column: " + p.get("checked_on", "") + "**.", "",
         "| row | goal | PAHT-CF H1 (record) | PPA-CF H1 (released print) | **PPA-CF H1-P (exported)** | basis |",
         "|---|---:|---:|---:|---:|---|"]
    a = {_key(r["name"]): r for r in h["rows"]}
    for r in p["rows"]:
        k = _key(r["name"])
        pa = PAHT_H1.get(k)
        hv = a.get(k)
        L.append(f"| {r['name']} | {r['goal']:g} | {pa if pa is not None else '-'} | "
                 f"{hv['value'] if hv else '-'} | **{r['value']}**{'' if r['pass'] else ' (below goal: ' + r.get('gated_by', 'FAIL') + ')'} | {r['basis']} |")
    L += ["", f"PPA H1 hip mount: inserts on the HB-6 basis scaled by knocked Z (abs_z); on the record rule (INS-Z, "
          f"hot x Z/XY): " + ", ".join(f"{x['name'].split(' (')[0]} {x['value']}" for x in h["hip_record_rule_rows"])
          + ". H1-P hip mount: " + p["hip_mount"]["hardware"] + ". Mount, screw positions and face unchanged.", "",
          "## Mass", "",
          "| body (printed halves + US2 clevises) | g | lb |", "|---|---:|---:|",
          f"| PAHT-CF H1 (released) | {PAHT_BODY_G:.1f} | {_lb(PAHT_BODY_G)} |",
          f"| PPA-CF H1 (same print) | {h['body_g']:.1f} | {_lb(h['body_g'])} |",
          f"| **PPA-CF H1-P** | **{p['body_g']:.1f}** | **{_lb(p['body_g'])}** |",
          f"| H1-P vs PAHT H1 | {p['delta_vs_paht_h1_g']:+.1f} | {p['delta_vs_paht_h1_g'] / 28.35:+.1f} oz |",
          f"| H1-P vs PPA H1 | {p['delta_vs_h1_ppa_g']:+.1f} | {p['delta_vs_h1_ppa_g'] / 28.35:+.1f} oz |", ""]
    L += ["## Print orientation per half (every set re-read with the layer normal along x or z)", "",
          "| basis | " + " | ".join(ORIENT) + " |", "|---|" + "---:|" * len(ORIENT)]
    for b in BASES:
        L.append(f"| H1 {b} fatigue | " + " | ".join(f"{h['orientation'][b][k]['fatigue']:.3f}" for k in ORIENT) + " |")
    for b in BASES:
        L.append(f"| H1-P {b} fatigue | " + " | ".join(f"{p['orientation'][b][k]['fatigue']:.3f}" for k in ORIENT) + " |")
    L += ["", "Lower / upper half layer normal (y = face down as released). Face down is best for both halves on "
          "every basis: turning a half on edge moves the frame's in-plane bending (sigma_xx in the struts, sigma_zz "
          "in the stays) across the layers.", ""]
    L += ["## Design steps", "",
          "Voxel-model steps (b, c) were checked on the 3 loop bases on the design voxels; export steps on all 4 bases "
          "on the exported STL re-rastered. The voxel steps over-read: exported as is, c3 kept only 2639 of the 7974 "
          "voxels it took off (5335 sat inside exact export features: the BL-053 US1 lug-fix hulls, the D50 hip "
          "boss), and smoothing rounded off a third of the one-voxel growth, so R1 fell 1.035 -> 0.987. Those "
          "feature voxels are frozen since (feature_mask), and the last steps were designed on the export's own "
          "utilisation.", "",
          "| step | checked on | from | u_lo | grow (u_hi) | thin layers | removed / added voxels | body g | R1 | "
          "static fatigue | strength | joint fatigue |", "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for x in p["steps"]:
        L.append(f"| {x['name']} | {x['geometry']} | {x['prev']} | {x['u_lo']:g} | {('yes (' + format(x['u_hi'], 'g') + ')') if x.get('grow') else 'no'} | "
                 f"{x.get('n_thin', 1)} | {x['removed']} / {x['added']} | {x['body_g_ppa']} | {x['cyc']} | "
                 f"{x['static_fatigue']} | {x['strength']} | {x['joint_fatigue']} |")
    L += ["", f"Chosen: **{p['final_iter']}**, exported and re-checked on the export (rows above).", ""]
    pr0, pr1 = h["print"], p["print"]
    L += ["## Printability on the H2S (PPA-CF, wearer face down)", "",
          "| half | plate contact mm2 | supported mm2 | support g (est / high) | filament g (high, +8 %) | spools | "
          "time h | bed fit |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for lab, pr in (("H1", pr0), ("H1-P", pr1)):
        for nm in ("lower", "upper"):
            q = pr[nm]
            L.append(f"| {lab} {nm} | {q['plate_contact_mm2']:.0f} | {q['supported_mm2']:.0f} | "
                     f"{q['support_g_ppa_est']:.0f} / {q['support_g_ppa_high']:.0f} | {q['filament_g_high_with_waste']:.0f} | "
                     f"{q['spools']:.2f}{' (swap)' if q['needs_spool_swap'] else ''} | {q['print_h_est']:.1f} | "
                     f"{'fits' if q['fits_h2s_340x320x340'] else 'NO'} |")
    L += ["", "## Coupons (register rows, not yet in the kit)", "", "| id | what | pass line | settles |",
          "|---|---|---|---|"]
    for c in rec["coupons"]:
        L.append(f"| {c['id']} | {c['what']}; {c['coupons']}{'; ' + c['load'] if c.get('load') else ''} | "
                 f"{c['pass']} | {c['settles']} |")
    L += ["", "## ASSUMPTIONS", ""]
    for a_ in rec["assumptions"]:
        L.append(f"- ASSUMPTION {a_['id']}: {a_['text']} Settled by: {a_['settled_by']}.")
    L += ["", "## Screenshots", ""] + [f"- `{q}`" for q in rec["screenshots"]] + [""]
    REC_MD.write_text("\n".join(L))
    return str(REC_MD)


# ================================================================================================ CLI
def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else "report"
    if cmd == "base":
        s0 = FI.baseline_solid()
        for mat in (a[1:] or ["ppa_design"]):
            check_body("h1", s0, mat=mat, orient=(mat == "ppa_design"))
        return 0
    if cmd == "finalize":
        finalize(a[1] if len(a) > 1 else FINAL_ITER)
        return 0
    if cmd == "eigen":
        run_eigen_h1p()
        return 0
    if cmd == "report":
        report()
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
